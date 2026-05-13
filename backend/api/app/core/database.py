"""Database connection và session management.

- Engine singleton với connection pooling
- FastAPI dependency để inject sessions
- Mỗi request có session riêng, auto cleanup
"""
from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()
# Engine singleton, thread-safe, connection pooling
engine = create_engine(settings.database_url, echo=False)

# Hàm này chỉ dùng cho testing. Production dùng Alembic migrations.
def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency: inject DB session vào endpoints.
    
    Session auto cleanup sau request. Không auto-commit.
    
    Usage:
        @router.get("/users/{id}")
        def get_user(id: int, session: Session = Depends(get_session)):
            return session.get(User, id)
    """
    with Session(engine) as session:
        yield session

# Chỉ dùng cho testing. Production dùng Alembic migrations.
def create_db_and_tables() -> None:
    """Tạo tables từ SQLModel definitions.
    
    Chỉ dùng cho testing. Production dùng Alembic migrations.
    """
    SQLModel.metadata.create_all(engine)
