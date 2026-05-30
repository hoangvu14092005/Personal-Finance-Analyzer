from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlmodel import Session, select

from app.core.database import create_db_and_tables, engine
from app.models.entities import (
    Budget,
    Category,
    Insight,
    Merchant,
    OcrResult,
    ReceiptLineItem,
    ReceiptUpload,
    Transaction,
    User,
)
from app.services.password_service import hash_password


def main() -> None:
    create_db_and_tables()
    now = datetime.now(tz=UTC)

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == "admin@example.com")).first()
        if user is None:
            user = User(
                email="admin@example.com",
                password_hash=hash_password("1"),
                full_name="Admin PFA Demo",
                currency="VND",
                timezone="Asia/Ho_Chi_Minh",
                locale="vi-VN",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        else:
            user.password_hash = hash_password("1")
            session.add(user)
            session.commit()
            session.refresh(user)

        if user.id is None:
            raise RuntimeError("Demo user id missing")

        category_specs = [
            ("Ăn uống", "#f59e0b"),
            ("Di chuyển", "#10b981"),
            ("Mua sắm", "#3b82f6"),
            ("Hóa đơn", "#ef4444"),
            ("Giải trí", "#8b5cf6"),
        ]
        categories: dict[str, Category] = {}
        for name, color in category_specs:
            category = session.exec(select(Category).where(Category.name == name, Category.user_id.is_(None))).first()
            if category is None:
                category = Category(name=name, color=color, is_system=True)
                session.add(category)
                session.commit()
                session.refresh(category)
            categories[name] = category

        merchant = session.exec(select(Merchant).where(Merchant.normalized_name == "highlands_coffee")).first()
        if merchant is None:
            merchant = Merchant(normalized_name="highlands_coffee", display_name="Highlands Coffee")
            session.add(merchant)
            session.commit()
            session.refresh(merchant)

        receipt = session.exec(select(ReceiptUpload).where(ReceiptUpload.user_id == user.id)).first()
        if receipt is None:
            receipt = ReceiptUpload(
                user_id=user.id,
                file_name="highlands-demo.jpg",
                content_type="image/jpeg",
                file_size_bytes=128000,
                storage_key="demo/highlands-demo.jpg",
                merchant_name="Highlands Coffee",
                receipt_date=date(2026, 5, 28),
                total_amount=Decimal("68000"),
                currency="VND",
                status="ready",
                ocr_status="succeeded",
                has_invoice=False,
            )
            session.add(receipt)
            session.commit()
            session.refresh(receipt)

            session.add(
                OcrResult(
                    receipt_upload_id=receipt.id,
                    provider="llm_vision",
                    raw_text="Highlands Coffee\nCa phe sua da 39000\nBanh Croissant 29000\nTong cong 68000",
                    confidence=0.92,
                    normalized_payload='{"merchant_name":"Highlands Coffee","total_amount":68000}',
                    status="ready",
                )
            )
            session.commit()

        tx_count = session.exec(select(Transaction).where(Transaction.user_id == user.id)).all()
        if not tx_count:
            food_id = categories["Ăn uống"].id
            move_id = categories["Di chuyển"].id
            shopping_id = categories["Mua sắm"].id
            bill_id = categories["Hóa đơn"].id
            txs = [
                Transaction(user_id=user.id, merchant_id=merchant.id, category_id=food_id, receipt_upload_id=receipt.id, raw_merchant_name="Highlands Coffee Q1", merchant_name="Highlands Coffee", amount=Decimal("68000"), currency="VND", transaction_date=date(2026, 5, 28), note="OCR demo đã xác nhận", source="receipt", status="confirmed", confirmed_at=now),
                Transaction(user_id=user.id, category_id=move_id, merchant_name="Grab", amount=Decimal("125000"), currency="VND", transaction_date=date(2026, 5, 27), note="Đi làm và gặp khách", source="manual", status="confirmed", confirmed_at=now),
                Transaction(user_id=user.id, category_id=shopping_id, merchant_name="Co.opmart", amount=Decimal("420000"), currency="VND", transaction_date=date(2026, 5, 25), note="Mua đồ gia đình", source="manual", status="confirmed", confirmed_at=now),
                Transaction(user_id=user.id, category_id=bill_id, merchant_name="EVN", amount=Decimal("310000"), currency="VND", transaction_date=date(2026, 5, 22), note="Tiền điện", source="manual", status="confirmed", confirmed_at=now),
            ]
            for tx in txs:
                session.add(tx)
            session.commit()

            linked_tx = session.exec(select(Transaction).where(Transaction.receipt_upload_id == receipt.id)).first()
            if linked_tx is not None:
                session.add_all([
                    ReceiptLineItem(user_id=user.id, receipt_upload_id=receipt.id, transaction_id=linked_tx.id, line_number=0, item_name="Cà phê sữa đá", quantity=Decimal("1"), unit_price=Decimal("39000"), total_price=Decimal("39000"), category_id=food_id),
                    ReceiptLineItem(user_id=user.id, receipt_upload_id=receipt.id, transaction_id=linked_tx.id, line_number=1, item_name="Bánh Croissant", quantity=Decimal("1"), unit_price=Decimal("29000"), total_price=Decimal("29000"), category_id=food_id),
                ])
                session.commit()

        budget_count = session.exec(select(Budget).where(Budget.user_id == user.id)).all()
        if not budget_count:
            for name, amount in [("Ăn uống", "300000"), ("Di chuyển", "500000"), ("Mua sắm", "1000000"), ("Hóa đơn", "800000")]:
                session.add(Budget(user_id=user.id, category_id=categories[name].id, period_month="2026-05", amount=Decimal(amount)))
            session.commit()

        insight = session.exec(select(Insight).where(Insight.user_id == user.id)).first()
        if insight is None:
            session.add(
                Insight(
                    user_id=user.id,
                    type="spending_pattern",
                    severity="info",
                    title="Ăn uống đang trong vùng kiểm soát",
                    summary="Dữ liệu demo cho thấy nhóm ăn uống còn nằm dưới hạn mức tháng 05/2026.",
                    evidence_json='[{"label":"Highlands Coffee","amount":68000}]',
                    actions_json='[{"label":"Xem giao dịch","href":"/transactions"}]',
                    range_start=date(2026, 5, 1),
                    range_end=date(2026, 5, 31),
                )
            )
            session.commit()

    print("Demo account ready: admin / 1")


if __name__ == "__main__":
    main()
