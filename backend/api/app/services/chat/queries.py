"""Chat query functions — tools cho LLM function calling (Phase 6.1).

Mỗi function:
- Nhận `session` + `user_id` bắt buộc (user isolation enforced).
- Trả về dict serializable (Decimal → str, date → ISO).
- Không raise exception khi không có data — trả empty/None có ý nghĩa.
- Tái sử dụng services sẵn có khi phù hợp.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlmodel import Session, col, func, select

from app.models.entities import Category, Invoice, ReceiptUpload, Transaction
from app.services.analytics import compute_summary
from app.services.budgets import compute_budget_usage
from app.services.date_ranges import (
    RangePreset,
    previous_period,
    resolve_range,
)


def _resolve_preset(preset: str) -> RangePreset:
    """Parse preset string → enum. Default 'this_month' nếu invalid."""
    try:
        return RangePreset(preset)
    except ValueError:
        return RangePreset.THIS_MONTH


def _decimal_str(value: Decimal) -> str:
    return f"{value:.2f}"


def _current_period_month() -> str:
    today = date.today()
    return f"{today.year:04d}-{today.month:02d}"


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _iso_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _linked_transaction_payload(transaction: Transaction | None) -> dict[str, Any] | None:
    if transaction is None or transaction.id is None:
        return None
    return {
        "transaction_id": transaction.id,
        "status": transaction.status,
        "transaction_date": transaction.transaction_date.isoformat(),
        "amount": _decimal_str(transaction.amount),
        "currency": transaction.currency,
    }


def _receipt_payload(
    receipt: ReceiptUpload,
    *,
    transaction: Transaction | None = None,
    invoice: Invoice | None = None,
) -> dict[str, Any]:
    return {
        "receipt_id": receipt.id,
        "file_name": receipt.file_name,
        "content_type": receipt.content_type,
        "status": receipt.status,
        "ocr_status": receipt.ocr_status,
        "merchant_name": receipt.merchant_name,
        "receipt_date": receipt.receipt_date.isoformat() if receipt.receipt_date else None,
        "total_amount": _decimal_str(receipt.total_amount) if receipt.total_amount else None,
        "currency": receipt.currency,
        "has_invoice": receipt.has_invoice,
        "invoice_id": invoice.id if invoice is not None else None,
        "created_at": _iso_datetime(receipt.created_at),
        "linked_transaction": _linked_transaction_payload(transaction),
    }


def query_spending_summary(
    session: Session,
    user_id: int,
    *,
    date_range: str = "this_month",
    category_name: str | None = None,
) -> dict[str, Any]:
    """Tổng chi tiêu + top categories trong khoảng thời gian.

    Returns dict với: total_spend, transaction_count, top_categories[], date_range info.
    """
    preset = _resolve_preset(date_range)
    current = resolve_range(preset)
    previous = previous_period(current, preset)
    summary = compute_summary(session, user_id, current, previous)

    top_cats = [
        {
            "name": c.name,
            "total": _decimal_str(c.total_amount),
            "count": c.transaction_count,
            "percentage": c.percentage,
        }
        for c in summary.top_categories
    ]

    # Filter by category_name nếu có
    if category_name:
        cat_lower = category_name.lower()
        filtered = [c for c in top_cats if cat_lower in str(c["name"]).lower()]
        if filtered:
            total_for_cat = sum(
                (Decimal(str(c["total"])) for c in filtered), Decimal("0"),
            )
            return {
                "total_spend": _decimal_str(total_for_cat),
                "transaction_count": sum(int(str(c["count"])) for c in filtered),
                "category": category_name,
                "period": f"{current.start.isoformat()} to {current.end.isoformat()}",
                "currency": "VND",
            }

    return {
        "total_spend": _decimal_str(summary.current.total_spend),
        "transaction_count": summary.current.transaction_count,
        "top_categories": top_cats[:5],
        "period": f"{current.start.isoformat()} to {current.end.isoformat()}",
        "currency": "VND",
    }


def search_transactions(
    session: Session,
    user_id: int,
    *,
    merchant: str | None = None,
    date_range: str | None = None,
    amount_min: float | None = None,
    amount_max: float | None = None,
    category_name: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Tìm kiếm giao dịch theo nhiều tiêu chí.

    Returns dict với: transactions[], total_count.
    """
    query = select(Transaction).where(Transaction.user_id == user_id)

    # Date range filter
    if date_range:
        preset = _resolve_preset(date_range)
        range_ = resolve_range(preset)
        query = query.where(Transaction.transaction_date >= range_.start)
        query = query.where(Transaction.transaction_date <= range_.end)

    # Merchant filter (LIKE with escaped wildcards)
    if merchant:
        escaped = merchant.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(col(Transaction.merchant_name).ilike(f"%{escaped}%"))

    # Amount range
    if amount_min is not None:
        query = query.where(Transaction.amount >= Decimal(str(amount_min)))
    if amount_max is not None:
        query = query.where(Transaction.amount <= Decimal(str(amount_max)))

    # Category filter by name (join)
    if category_name:
        cat_lower = category_name.lower()
        cat_ids_query = select(Category.id).where(
            func.lower(Category.name).contains(cat_lower),
        )
        query = query.where(col(Transaction.category_id).in_(cat_ids_query))

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = session.exec(count_query).one()

    # Fetch with limit
    query = query.order_by(
        col(Transaction.transaction_date).desc(),
        col(Transaction.id).desc(),
    ).limit(min(limit, 50))

    rows = session.exec(query).all()

    transactions = [
        {
            "id": t.id,
            "merchant_name": t.merchant_name,
            "amount": _decimal_str(t.amount),
            "currency": t.currency,
            "transaction_date": t.transaction_date.isoformat(),
            "note": t.note,
        }
        for t in rows
    ]

    return {
        "transactions": transactions,
        "total_count": int(total_count),
        "showing": len(transactions),
    }


def search_receipts(
    session: Session,
    user_id: int,
    *,
    receipt_date: str | None = None,
    created_date: str | None = None,
    merchant: str | None = None,
    status: str | None = None,
    ocr_status: str | None = None,
    has_transaction: bool | None = None,
    has_invoice: bool | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Tra cứu chứng từ/hóa đơn theo metadata của receipt upload.

    Dùng cho intent hỏi về chứng từ: hóa đơn đã upload, hóa đơn theo ngày
    trên chứng từ, trạng thái OCR, hoặc receipt/invoice có transaction chưa.
    Không dùng kết quả này để tính tổng chi tiêu chính thức.
    """
    capped_limit = min(max(limit, 1), 50)
    parsed_receipt_date = _parse_iso_date(receipt_date)
    parsed_created_date = _parse_iso_date(created_date)

    statement = select(ReceiptUpload).where(ReceiptUpload.user_id == user_id)
    if parsed_receipt_date is not None:
        statement = statement.where(ReceiptUpload.receipt_date == parsed_receipt_date)
    if parsed_created_date is not None:
        statement = statement.where(func.date(ReceiptUpload.created_at) == parsed_created_date)
    if merchant:
        escaped = merchant.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(col(ReceiptUpload.merchant_name).ilike(f"%{escaped}%"))
    if status:
        statement = statement.where(ReceiptUpload.status == status)
    if ocr_status:
        statement = statement.where(ReceiptUpload.ocr_status == ocr_status)
    if has_invoice is not None:
        statement = statement.where(ReceiptUpload.has_invoice == has_invoice)

    rows = list(
        session.exec(
            statement.order_by(col(ReceiptUpload.created_at).desc(), col(ReceiptUpload.id).desc()),
        ).all(),
    )
    receipt_ids = [receipt.id for receipt in rows if receipt.id is not None]

    tx_by_receipt: dict[int, Transaction] = {}
    if receipt_ids:
        tx_rows = session.exec(
            select(Transaction).where(
                Transaction.user_id == user_id,
                col(Transaction.receipt_upload_id).in_(receipt_ids),
            ),
        ).all()
        tx_by_receipt = {
            tx.receipt_upload_id: tx
            for tx in tx_rows
            if tx.receipt_upload_id is not None
        }

    if has_transaction is not None:
        rows = [
            receipt
            for receipt in rows
            if ((receipt.id in tx_by_receipt) if receipt.id is not None else False)
            == has_transaction
        ]
        receipt_ids = [receipt.id for receipt in rows if receipt.id is not None]

    invoice_by_receipt: dict[int, Invoice] = {}
    if receipt_ids:
        invoice_rows = session.exec(
            select(Invoice).where(
                Invoice.user_id == user_id,
                col(Invoice.receipt_upload_id).in_(receipt_ids),
            ),
        ).all()
        invoice_by_receipt = {invoice.receipt_upload_id: invoice for invoice in invoice_rows}

    page_rows = rows[:capped_limit]
    receipts = [
        _receipt_payload(
            receipt,
            transaction=tx_by_receipt.get(receipt.id or -1),
            invoice=invoice_by_receipt.get(receipt.id or -1),
        )
        for receipt in page_rows
    ]

    return {
        "receipts": receipts,
        "total_count": len(rows),
        "showing": len(receipts),
        "source_of_truth_note": (
            "Receipt/Invoice là chứng từ; tổng chi tiêu chính thức nằm ở transactions."
        ),
    }


def lookup_transaction_receipts(
    session: Session,
    user_id: int,
    *,
    merchant: str | None = None,
    transaction_date: str | None = None,
    date_range: str | None = None,
    has_receipt: bool | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Tìm giao dịch và cho biết mỗi giao dịch có chứng từ liên kết hay không."""
    capped_limit = min(max(limit, 1), 50)
    parsed_transaction_date = _parse_iso_date(transaction_date)

    statement = select(Transaction).where(Transaction.user_id == user_id)
    if merchant:
        escaped = merchant.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        statement = statement.where(col(Transaction.merchant_name).ilike(f"%{escaped}%"))
    if parsed_transaction_date is not None:
        statement = statement.where(Transaction.transaction_date == parsed_transaction_date)
    elif date_range:
        preset = _resolve_preset(date_range)
        range_ = resolve_range(preset)
        statement = statement.where(Transaction.transaction_date >= range_.start)
        statement = statement.where(Transaction.transaction_date <= range_.end)
    if has_receipt is not None:
        if has_receipt:
            statement = statement.where(Transaction.receipt_upload_id.is_not(None))  # type: ignore[union-attr]
        else:
            statement = statement.where(Transaction.receipt_upload_id.is_(None))  # type: ignore[union-attr]

    rows = list(
        session.exec(
            statement.order_by(
                col(Transaction.transaction_date).desc(),
                col(Transaction.id).desc(),
            ),
        ).all(),
    )
    receipt_ids = [tx.receipt_upload_id for tx in rows if tx.receipt_upload_id is not None]

    receipt_by_id: dict[int, ReceiptUpload] = {}
    if receipt_ids:
        receipt_rows = session.exec(
            select(ReceiptUpload).where(
                ReceiptUpload.user_id == user_id,
                col(ReceiptUpload.id).in_(receipt_ids),
            ),
        ).all()
        receipt_by_id = {receipt.id: receipt for receipt in receipt_rows if receipt.id is not None}

    transactions = []
    for tx in rows[:capped_limit]:
        receipt = receipt_by_id.get(tx.receipt_upload_id or -1)
        transactions.append({
            "transaction_id": tx.id,
            "merchant_name": tx.merchant_name,
            "amount": _decimal_str(tx.amount),
            "currency": tx.currency,
            "transaction_date": tx.transaction_date.isoformat(),
            "source": tx.source,
            "status": tx.status,
            "has_receipt": receipt is not None,
            "receipt": _receipt_payload(receipt, transaction=tx) if receipt is not None else None,
        })

    return {
        "transactions": transactions,
        "total_count": len(rows),
        "showing": len(transactions),
    }


def get_budget_status(
    session: Session,
    user_id: int,
    *,
    period_month: str | None = None,
) -> dict[str, Any]:
    """Trạng thái budget cho tháng chỉ định (default: tháng hiện tại).

    Returns dict với: budgets[], period_month.
    """
    period = period_month or _current_period_month()
    usages = compute_budget_usage(session, user_id, period)

    budgets = [
        {
            "category_name": u.category_name,
            "budget_amount": _decimal_str(u.budget_amount),
            "spent_amount": _decimal_str(u.spent_amount),
            "remaining": _decimal_str(u.remaining_amount),
            "percent_used": u.percent_used,
            "status": u.status,
        }
        for u in usages
    ]

    return {
        "budgets": budgets,
        "period_month": period,
        "total_budgets": len(budgets),
    }


def compare_periods(
    session: Session,
    user_id: int,
    *,
    period_a: str = "this_month",
    period_b: str = "last_month",
) -> dict[str, Any]:
    """So sánh chi tiêu giữa 2 khoảng thời gian.

    Returns dict với: period_a info, period_b info, delta.
    """
    preset_a = _resolve_preset(period_a)
    preset_b = _resolve_preset(period_b)

    range_a = resolve_range(preset_a)
    range_b = resolve_range(preset_b)

    prev_a = previous_period(range_a, preset_a)
    prev_b = previous_period(range_b, preset_b)

    summary_a = compute_summary(session, user_id, range_a, prev_a)
    summary_b = compute_summary(session, user_id, range_b, prev_b)

    delta = summary_a.current.total_spend - summary_b.current.total_spend
    if summary_b.current.total_spend > 0:
        delta_pct = float(
            round((delta / summary_b.current.total_spend) * Decimal("100"), 2),
        )
    else:
        delta_pct = None

    return {
        "period_a": {
            "label": period_a,
            "range": f"{range_a.start.isoformat()} to {range_a.end.isoformat()}",
            "total_spend": _decimal_str(summary_a.current.total_spend),
            "transaction_count": summary_a.current.transaction_count,
        },
        "period_b": {
            "label": period_b,
            "range": f"{range_b.start.isoformat()} to {range_b.end.isoformat()}",
            "total_spend": _decimal_str(summary_b.current.total_spend),
            "transaction_count": summary_b.current.transaction_count,
        },
        "delta_amount": _decimal_str(delta),
        "delta_percent": delta_pct,
        "currency": "VND",
    }


def get_top_merchants(
    session: Session,
    user_id: int,
    *,
    date_range: str = "this_month",
    limit: int = 10,
) -> dict[str, Any]:
    """Top merchants theo tổng chi tiêu.

    Returns dict với: merchants[], period.
    """
    from app.services import analytics_queries as aq

    preset = _resolve_preset(date_range)
    range_ = resolve_range(preset)

    rows = aq.query_merchant_aggregates(
        session, user_id, range_, limit=min(limit, 20), exclude_unknown=True,
    )
    merchants = [
        {
            "merchant_name": row.merchant_name,
            "total_spend": _decimal_str(row.total_amount),
            "transaction_count": row.transaction_count,
        }
        for row in rows
    ]

    return {
        "merchants": merchants,
        "period": f"{range_.start.isoformat()} to {range_.end.isoformat()}",
        "currency": "VND",
    }


def get_spending_by_day(
    session: Session,
    user_id: int,
    *,
    date_range: str = "this_month",
) -> dict[str, Any]:
    """Chi tiêu theo ngày trong khoảng thời gian.

    Returns dict với: days[], period, total.
    """
    from app.services import analytics_queries as aq

    preset = _resolve_preset(date_range)
    range_ = resolve_range(preset)

    rows = aq.query_daily_aggregates(session, user_id, range_)
    days = [
        {
            "date": day.isoformat(),
            "total_spend": _decimal_str(total),
            "transaction_count": count,
        }
        for day, total, count in rows
    ]

    grand_total = sum((Decimal(str(d["total_spend"])) for d in days), Decimal("0"))

    return {
        "days": days,
        "period": f"{range_.start.isoformat()} to {range_.end.isoformat()}",
        "total_spend": _decimal_str(grand_total),
        "total_days_with_spending": len(days),
        "currency": "VND",
    }


def get_recent_transactions(
    session: Session,
    user_id: int,
    *,
    limit: int = 10,
) -> dict[str, Any]:
    """N giao dịch gần nhất của user.

    Returns dict với: transactions[], count.
    """
    capped_limit = min(limit, 50)

    statement = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(
            col(Transaction.transaction_date).desc(),
            col(Transaction.id).desc(),
        )
        .limit(capped_limit)
    )

    rows = session.exec(statement).all()

    transactions = [
        {
            "id": t.id,
            "merchant_name": t.merchant_name,
            "amount": _decimal_str(t.amount),
            "currency": t.currency,
            "transaction_date": t.transaction_date.isoformat(),
            "note": t.note,
        }
        for t in rows
    ]

    return {
        "transactions": transactions,
        "count": len(transactions),
    }


def get_product_breakdown(
    session: Session,
    user_id: int,
    *,
    date_range: str = "this_month",
    limit: int = 10,
) -> dict[str, Any]:
    """Top sản phẩm/món theo tổng chi, từ line items hóa đơn đã confirm.

    Dùng cho câu hỏi "tôi mua món gì nhiều nhất / chi cho sản phẩm nào".
    """
    from app.services.analytics import compute_product_breakdown

    preset = _resolve_preset(date_range)
    range_ = resolve_range(preset)
    products = compute_product_breakdown(session, user_id, range_, limit=min(max(limit, 1), 50))
    return {
        "products": [
            {
                "item_name": p.item_name,
                "total_amount": _decimal_str(p.total_amount),
                "total_quantity": _decimal_str(p.total_quantity),
                "line_count": p.line_count,
                "percentage": p.percentage,
            }
            for p in products
        ],
        "period": f"{range_.start.isoformat()} to {range_.end.isoformat()}",
        "currency": "VND",
        "note": "Chỉ tính line items của hóa đơn đã xác nhận thành giao dịch.",
    }


def get_tax_summary(
    session: Session,
    user_id: int,
    *,
    date_range: str = "this_month",
) -> dict[str, Any]:
    """Tổng VAT đã trả + top người bán, từ hóa đơn đã confirm.

    Dùng cho câu hỏi "tôi đã trả bao nhiêu thuế VAT / mua nhiều nhất ở đâu (theo MST)".
    """
    from app.services.analytics import compute_vat_summary

    preset = _resolve_preset(date_range)
    range_ = resolve_range(preset)
    summary = compute_vat_summary(session, user_id, range_)
    return {
        "subtotal_before_tax": _decimal_str(summary.subtotal_before_tax),
        "total_tax": _decimal_str(summary.total_tax),
        "grand_total": _decimal_str(summary.grand_total),
        "invoice_count": summary.invoice_count,
        "effective_tax_rate": summary.effective_tax_rate,
        "top_sellers": [
            {
                "seller_name": s.seller_name,
                "seller_tax_id": s.seller_tax_id,
                "total_amount": _decimal_str(s.total_amount),
                "invoice_count": s.invoice_count,
                "percentage": s.percentage,
            }
            for s in summary.top_sellers
        ],
        "period": f"{range_.start.isoformat()} to {range_.end.isoformat()}",
        "currency": "VND",
    }


def diagnose_spending_change(
    session: Session,
    user_id: int,
    *,
    date_range: str = "this_month",
) -> dict[str, Any]:
    """Phân rã VÌ SAO chi tiêu thay đổi so với kỳ trước (category + merchant).

    Dùng cho câu hỏi "vì sao tháng này tôi tiêu nhiều hơn / cái gì làm chi tăng".
    """
    from app.services.diagnostics import compute_spending_diagnostics

    preset = _resolve_preset(date_range)
    current = resolve_range(preset)
    previous = previous_period(current, preset)
    diag = compute_spending_diagnostics(session, user_id, current, previous)
    return {
        "current_total": _decimal_str(diag.current_total),
        "previous_total": _decimal_str(diag.previous_total),
        "delta_amount": _decimal_str(diag.delta_amount),
        "delta_percent": diag.delta_percent,
        "drivers": [
            {
                "category_name": d.category_name,
                "current_amount": _decimal_str(d.current_amount),
                "previous_amount": _decimal_str(d.previous_amount),
                "delta_amount": _decimal_str(d.delta_amount),
                "delta_percent": d.delta_percent,
                "direction": d.direction,
                "top_merchants": [
                    {
                        "merchant_name": m.merchant_name,
                        "delta_amount": _decimal_str(m.delta_amount),
                    }
                    for m in d.top_merchants
                ],
            }
            for d in diag.drivers
        ],
        "currency": "VND",
    }


def forecast_month_spending(
    session: Session,
    user_id: int,
) -> dict[str, Any]:
    """Dự báo chi cuối tháng + cảnh báo budget nào sắp vượt (run-rate).

    Dùng cho câu hỏi "cuối tháng tôi tiêu hết bao nhiêu / có vượt ngân sách không".
    """
    from app.services.forecast import compute_forecast

    forecast = compute_forecast(session, user_id)
    return {
        "period_month": forecast.month.period_month,
        "days_elapsed": forecast.month.days_elapsed,
        "days_in_month": forecast.month.days_in_month,
        "spent_so_far": _decimal_str(forecast.month.spent_so_far),
        "daily_run_rate": _decimal_str(forecast.month.daily_run_rate),
        "projected_total": _decimal_str(forecast.month.projected_total),
        "budgets": [
            {
                "category_name": b.category_name,
                "budget_amount": _decimal_str(b.budget_amount),
                "spent_so_far": _decimal_str(b.spent_so_far),
                "projected_spend": _decimal_str(b.projected_spend),
                "projected_percent": b.projected_percent,
                "status": b.status,
                "projected_exceed_date": (
                    b.projected_exceed_date.isoformat() if b.projected_exceed_date else None
                ),
            }
            for b in forecast.budgets
        ],
        "currency": "VND",
    }


__all__ = [
    "compare_periods",
    "diagnose_spending_change",
    "forecast_month_spending",
    "get_budget_status",
    "get_product_breakdown",
    "get_recent_transactions",
    "get_spending_by_day",
    "get_tax_summary",
    "get_top_merchants",
    "lookup_transaction_receipts",
    "query_spending_summary",
    "search_receipts",
    "search_transactions",
]
