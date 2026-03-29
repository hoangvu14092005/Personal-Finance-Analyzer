from __future__ import annotations

import os
from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://pfa:pfa@localhost:5432/pfa",
)

engine = create_engine(DATABASE_URL, echo=False)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
