from __future__ import annotations

from app.core.database import engine
from app.models.entities import Category
from sqlmodel import Session, select

DEFAULT_CATEGORIES: tuple[str, ...] = (
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Health",
    "Education",
    "Entertainment",
    "Other",
)


def seed_default_categories() -> int:
    created = 0
    with Session(engine) as session:
        for category_name in DEFAULT_CATEGORIES:
            statement = select(Category).where(
                Category.user_id.is_(None),
                Category.name == category_name,
            )
            existing = session.exec(statement).first()
            if existing is not None:
                continue

            session.add(
                Category(
                    user_id=None,
                    name=category_name,
                    is_system=True,
                ),
            )
            created += 1

        session.commit()
    return created


if __name__ == "__main__":
    total = seed_default_categories()
    print(f"Seeded {total} default categories.")
