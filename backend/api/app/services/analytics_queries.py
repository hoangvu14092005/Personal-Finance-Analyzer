"""Unified BI query layer (G2).

Nơi DUY NHẤT chứa các câu query đọc dữ liệu cho BI. Mọi chiều phân tích
(transactions, sản phẩm/line-items, VAT/invoices, thống kê hóa đơn) đều đọc
trực tiếp từ DB ở đây — real-time, KHÔNG cache. `analytics.py` (orchestration)
và `insights.py` đều gọi tầng này để số liệu nhất quán, và G3 (diagnostic/
predictive/LLM) sau này tái dùng cùng nguồn.

Nguyên tắc nguồn sự thật:
- Tiền = transaction đã confirm (bảng `transactions`).
- Chiều sản phẩm & VAT chỉ tính line-item/invoice ĐÃ gắn `transaction_id`
  (tức receipt đã được user confirm) → BI phản ánh đúng những gì user đã chốt,
  cập nhật ngay khi confirm (real-time theo phương án A).
- VND-only: toàn bộ tiền giả định cùng đơn vị VND (xem G2 decision).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlmodel import Session, col, func, select

from app.models.entities import (
    Invoice,
    ReceiptLineItem,
    ReceiptUpload,
    Transaction,
)
from app.services.date_ranges import DateRange

# ---------------------------------------------------------------------------
# Raw aggregate row types (data layer output — KHÔNG chứa % hay format hiển thị).
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CategoryAggRow:
    category_id: int | None
    total_amount: Decimal
    transaction_count: int


@dataclass(frozen=True, slots=True)
class MerchantAggRow:
    merchant_name: str
    total_amount: Decimal
    transaction_count: int


@dataclass(frozen=True, slots=True)
class ProductAggRow:
    item_name: str
    total_amount: Decimal
    total_quantity: Decimal
    line_count: int


@dataclass(frozen=True, slots=True)
class SellerAggRow:
    seller_name: str
    seller_tax_id: str | None
    total_amount: Decimal
    invoice_count: int


@dataclass(frozen=True, slots=True)
class VatTotals:
    subtotal_before_tax: Decimal
    total_tax: Decimal
    grand_total: Decimal
    invoice_count: int


@dataclass(frozen=True, slots=True)
class ReceiptStats:
    total_receipts: int
    ready_count: int
    failed_count: int
    pending_count: int
    with_invoice_count: int
    confirmed_count: int  # receipts đã thành transaction


def _decimal(value: object) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal("0")


# ---------------------------------------------------------------------------
# Transactions (nguồn sự thật tiền)
# ---------------------------------------------------------------------------


def query_period_totals(
    session: Session,
    user_id: int,
    range_: DateRange,
) -> tuple[Decimal, int]:
    """SUM(amount) + COUNT(*) cho transactions trong range. Trả (total, count)."""
    statement = (
        select(
            func.coalesce(func.sum(Transaction.amount), 0),
            func.count(Transaction.id),
        )
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
    )
    total_raw, count_raw = session.exec(statement).one()
    return _decimal(total_raw), int(count_raw or 0)


def query_category_aggregates(
    session: Session,
    user_id: int,
    range_: DateRange,
    *,
    limit: int | None = None,
) -> list[CategoryAggRow]:
    """GROUP BY category_id, SUM(amount) DESC. category_id=None = chưa phân loại."""
    total_expr = func.coalesce(func.sum(Transaction.amount), 0).label("total")
    statement = (
        select(
            Transaction.category_id,
            total_expr,
            func.count(Transaction.id).label("cnt"),
        )
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
        .group_by(col(Transaction.category_id))
        .order_by(total_expr.desc())
    )
    if limit is not None:
        statement = statement.limit(limit)
    return [
        CategoryAggRow(
            category_id=row[0],
            total_amount=_decimal(row[1]),
            transaction_count=int(row[2] or 0),
        )
        for row in session.exec(statement).all()
    ]


def query_merchant_aggregates(
    session: Session,
    user_id: int,
    range_: DateRange,
    *,
    limit: int = 10,
    exclude_unknown: bool = False,
) -> list[MerchantAggRow]:
    """Top merchants theo tổng chi.

    - `exclude_unknown=False` (mặc định, hành vi dashboard): merchant rỗng/None
      gom vào 'Không rõ'.
    - `exclude_unknown=True` (hành vi chat tool cũ): loại bỏ giao dịch không có
      merchant_name khỏi kết quả.
    """
    if exclude_unknown:
        merchant_expr = Transaction.merchant_name
    else:
        merchant_expr = func.coalesce(Transaction.merchant_name, "Không rõ")
    merchant_label = merchant_expr.label("merchant")
    total_expr = func.coalesce(func.sum(Transaction.amount), 0).label("total")
    statement = (
        select(merchant_label, total_expr, func.count(Transaction.id).label("cnt"))
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
    )
    if exclude_unknown:
        statement = statement.where(
            col(Transaction.merchant_name).is_not(None),
        ).where(Transaction.merchant_name != "")
    statement = (
        statement.group_by(merchant_label)
        .order_by(total_expr.desc())
        .limit(limit)
    )
    return [
        MerchantAggRow(
            merchant_name=str(row[0] or "Không rõ"),
            total_amount=_decimal(row[1]),
            transaction_count=int(row[2] or 0),
        )
        for row in session.exec(statement).all()
    ]


def query_daily_aggregates(
    session: Session,
    user_id: int,
    range_: DateRange,
) -> list[tuple[date, Decimal, int]]:
    """SUM(amount) + COUNT theo từng ngày có giao dịch trong range, sort ngày ASC.

    Chỉ trả các ngày CÓ giao dịch (giống chat tool get_spending_by_day cũ).
    """
    statement = (
        select(
            Transaction.transaction_date,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("cnt"),
        )
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
        .group_by(col(Transaction.transaction_date))
        .order_by(col(Transaction.transaction_date).asc())
    )
    return [
        (row[0], _decimal(row[1]), int(row[2] or 0))
        for row in session.exec(statement).all()
    ]


def query_transactions_for_range(
    session: Session,
    user_id: int,
    range_: DateRange,
) -> list[Transaction]:
    """Toàn bộ transaction trong range, sort ngày ASC (cho trend/calendar/anomaly)."""
    statement = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
        .order_by(col(Transaction.transaction_date).asc(), col(Transaction.id).asc())
    )
    return list(session.exec(statement).all())


def query_merchant_aggregates_for_category(
    session: Session,
    user_id: int,
    range_: DateRange,
    category_id: int | None,
    *,
    limit: int = 5,
) -> list[MerchantAggRow]:
    """Top merchants TRONG MỘT category cụ thể (drill-down cho diagnostics).

    `category_id=None` → giao dịch chưa phân loại.
    """
    merchant_expr = func.coalesce(Transaction.merchant_name, "Không rõ").label("merchant")
    total_expr = func.coalesce(func.sum(Transaction.amount), 0).label("total")
    statement = (
        select(merchant_expr, total_expr, func.count(Transaction.id).label("cnt"))
        .where(Transaction.user_id == user_id)
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
    )
    if category_id is None:
        statement = statement.where(col(Transaction.category_id).is_(None))
    else:
        statement = statement.where(Transaction.category_id == category_id)
    statement = (
        statement.group_by(merchant_expr)
        .order_by(total_expr.desc())
        .limit(limit)
    )
    return [
        MerchantAggRow(
            merchant_name=str(row[0] or "Không rõ"),
            total_amount=_decimal(row[1]),
            transaction_count=int(row[2] or 0),
        )
        for row in session.exec(statement).all()
    ]


# ---------------------------------------------------------------------------
# Sản phẩm / line items (từ receipt_line_items đã confirm)
# ---------------------------------------------------------------------------


def query_product_aggregates(
    session: Session,
    user_id: int,
    range_: DateRange,
    *,
    limit: int = 20,
) -> list[ProductAggRow]:
    """Top sản phẩm theo tổng chi, từ receipt_line_items ĐÃ gắn transaction.

    Join `receipt_line_items` -> `transactions` để lọc theo ngày giao dịch + chỉ
    tính line item của receipt đã confirm (transaction_id NOT NULL). Gom theo
    tên sản phẩm chuẩn hóa (lower + trim).
    """
    name_expr = func.lower(func.trim(ReceiptLineItem.item_name)).label("name")
    total_expr = func.coalesce(func.sum(ReceiptLineItem.total_price), 0).label("total")
    qty_expr = func.coalesce(func.sum(ReceiptLineItem.quantity), 0).label("qty")
    statement = (
        select(
            name_expr,
            total_expr,
            qty_expr,
            func.count(ReceiptLineItem.id).label("cnt"),
        )
        .join(Transaction, col(ReceiptLineItem.transaction_id) == Transaction.id)
        .where(ReceiptLineItem.user_id == user_id)
        .where(col(ReceiptLineItem.transaction_id).is_not(None))
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
        .group_by(name_expr)
        .order_by(total_expr.desc())
        .limit(limit)
    )
    return [
        ProductAggRow(
            item_name=str(row[0] or ""),
            total_amount=_decimal(row[1]),
            total_quantity=_decimal(row[2]),
            line_count=int(row[3] or 0),
        )
        for row in session.exec(statement).all()
    ]


# ---------------------------------------------------------------------------
# VAT / invoices (từ invoices đã confirm)
# ---------------------------------------------------------------------------


def query_vat_totals(
    session: Session,
    user_id: int,
    range_: DateRange,
) -> VatTotals:
    """Tổng tiền hàng / thuế / thanh toán từ invoices đã gắn transaction trong range."""
    statement = (
        select(
            func.coalesce(func.sum(Invoice.subtotal_before_tax), 0),
            func.coalesce(func.sum(Invoice.total_tax), 0),
            func.coalesce(func.sum(Invoice.grand_total), 0),
            func.count(Invoice.id),
        )
        .join(Transaction, col(Invoice.transaction_id) == Transaction.id)
        .where(Invoice.user_id == user_id)
        .where(col(Invoice.transaction_id).is_not(None))
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
    )
    sub_raw, tax_raw, grand_raw, count_raw = session.exec(statement).one()
    return VatTotals(
        subtotal_before_tax=_decimal(sub_raw),
        total_tax=_decimal(tax_raw),
        grand_total=_decimal(grand_raw),
        invoice_count=int(count_raw or 0),
    )


def query_seller_aggregates(
    session: Session,
    user_id: int,
    range_: DateRange,
    *,
    limit: int = 10,
) -> list[SellerAggRow]:
    """Top người bán theo tổng tiền thanh toán (grand_total), từ invoices đã confirm."""
    seller_expr = func.coalesce(Invoice.seller_name, "Không rõ").label("seller")
    total_expr = func.coalesce(func.sum(Invoice.grand_total), 0).label("total")
    statement = (
        select(
            seller_expr,
            Invoice.seller_tax_id,
            total_expr,
            func.count(Invoice.id).label("cnt"),
        )
        .join(Transaction, col(Invoice.transaction_id) == Transaction.id)
        .where(Invoice.user_id == user_id)
        .where(col(Invoice.transaction_id).is_not(None))
        .where(Transaction.transaction_date >= range_.start)
        .where(Transaction.transaction_date <= range_.end)
        .group_by(seller_expr, col(Invoice.seller_tax_id))
        .order_by(total_expr.desc())
        .limit(limit)
    )
    return [
        SellerAggRow(
            seller_name=str(row[0] or "Không rõ"),
            seller_tax_id=row[1],
            total_amount=_decimal(row[2]),
            invoice_count=int(row[3] or 0),
        )
        for row in session.exec(statement).all()
    ]


# ---------------------------------------------------------------------------
# Thống kê hóa đơn (receipt_uploads — pipeline stats, lọc theo created_at)
# ---------------------------------------------------------------------------


def query_receipt_stats(
    session: Session,
    user_id: int,
    range_: DateRange,
) -> ReceiptStats:
    """Thống kê pipeline hóa đơn trong range (theo ngày tạo).

    Khác với tiền: stats này là về luồng upload/OCR nên lọc theo `created_at`,
    không phụ thuộc confirm. `confirmed_count` = số receipt đã có transaction.
    """
    rows = list(
        session.exec(
            select(ReceiptUpload)
            .where(ReceiptUpload.user_id == user_id)
            .where(func.date(ReceiptUpload.created_at) >= range_.start)
            .where(func.date(ReceiptUpload.created_at) <= range_.end),
        ).all(),
    )
    receipt_ids = [r.id for r in rows if r.id is not None]
    confirmed_ids: set[int] = set()
    if receipt_ids:
        confirmed_rows = session.exec(
            select(Transaction.receipt_upload_id)
            .where(Transaction.user_id == user_id)
            .where(col(Transaction.receipt_upload_id).in_(receipt_ids)),
        ).all()
        confirmed_ids = {rid for rid in confirmed_rows if rid is not None}

    ready = sum(1 for r in rows if r.ocr_status == "succeeded")
    failed = sum(1 for r in rows if r.ocr_status == "failed")
    pending = sum(1 for r in rows if r.ocr_status in {"pending", "running"})
    with_invoice = sum(1 for r in rows if r.has_invoice)
    return ReceiptStats(
        total_receipts=len(rows),
        ready_count=ready,
        failed_count=failed,
        pending_count=pending,
        with_invoice_count=with_invoice,
        confirmed_count=len(confirmed_ids),
    )


__all__ = [
    "CategoryAggRow",
    "MerchantAggRow",
    "ProductAggRow",
    "ReceiptStats",
    "SellerAggRow",
    "VatTotals",
    "query_category_aggregates",
    "query_daily_aggregates",
    "query_merchant_aggregates",
    "query_merchant_aggregates_for_category",
    "query_period_totals",
    "query_product_aggregates",
    "query_receipt_stats",
    "query_seller_aggregates",
    "query_transactions_for_range",
    "query_vat_totals",
]
