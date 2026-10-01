"""SQLAlchemy engine and session management.

SQLite is deliberately supported for local development and tests. Production
should use PostgreSQL through ``DATABASE_URL``.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""


settings = get_settings()
_engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    if settings.database_url in {"sqlite://", "sqlite:///:memory:"}:
        _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(settings.database_url, **_engine_kwargs)

# SQLite does not enable FK constraints by default. Enabling them keeps account
# deletion and meal ownership semantics consistent with PostgreSQL.
if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped database session and always close it."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables for the local zero-configuration experience.

    Production deployments should run Alembic migrations before starting the
    application; ``create_all`` is retained for SQLite demos and tests.
    """

    # Importing the package registers every model with Base.metadata.
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
