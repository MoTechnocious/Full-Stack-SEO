"""Engine + session management.

Uses ``DATABASE_URL`` (default SQLite for dev/tests; set to Postgres in prod).
``get_session`` is a FastAPI dependency and is overridden with a test engine in
the test-suite.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


def _connect_args(url: str) -> dict[str, object]:
    return {"check_same_thread": False} if url.startswith("sqlite") else {}


def _build_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url,
        echo=settings.db_echo,
        connect_args=_connect_args(settings.database_url),
    )


engine: Engine = _build_engine()


def init_db(bind: Engine | None = None) -> None:
    """Create all tables. Import side-effect of ``app.db`` registers the models.

    Dev/test convenience only: production schema changes are managed with
    Alembic (``cd backend && alembic upgrade head`` — see backend/alembic/ and
    docs/DEPLOYMENT.md "Database migrations"). ``create_all`` is a no-op for
    tables that already exist, so running it against a migrated database is
    harmless but never use it to evolve a production schema.
    """
    import app.db  # noqa: F401  (ensure models are imported/registered)

    SQLModel.metadata.create_all(bind or engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a DB session."""
    with Session(engine) as session:
        yield session
