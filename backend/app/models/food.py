"""Food reference data model.

Nutrients are stored for an explicit basis (for example 100 g or one piece),
never as unexplained magic numbers. ``source`` and ``confidence`` are exposed
with every food so clients can distinguish reference data from estimates.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, new_id


class Food(Base):
    __tablename__ = "foods"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(160), nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    basis_quantity: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    basis_unit: Mapped[str] = mapped_column(String(24), nullable=False, default="g")
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbohydrates_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiber_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sugar_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sodium_mg: Mapped[float | None] = mapped_column(Float, nullable=True)
    vitamins: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    minerals: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    items: Mapped[list["MealItem"]] = relationship("MealItem", back_populates="food")


from app.models.meal import MealItem  # noqa: E402,F401

__all__ = ["Food"]
