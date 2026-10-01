"""Shared SQLAlchemy declarative base and identifier helper."""

from uuid import uuid4

from app.core.database import Base


def new_id() -> str:
    """Return a URL-safe UUID string suitable for public resource identifiers."""

    return str(uuid4())


__all__ = ["Base", "new_id"]
