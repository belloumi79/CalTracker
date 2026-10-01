"""Meal, meal item, and optional hydration models."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, new_id


class Meal(Base):
    __tablename__ = "meals"
    __table_args__ = (Index("ix_meals_user_eaten_at", "user_id", "eaten_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    meal_type: Mapped[str] = mapped_column(String(24), nullable=False)
    eaten_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="meals")
    items: Mapped[list["MealItem"]] = relationship(
        "MealItem", back_populates="meal", cascade="all, delete-orphan", passive_deletes=True
    )


class MealItem(Base):
    __tablename__ = "meal_items"
    __table_args__ = (Index("ix_meal_items_meal_id", "meal_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    meal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meals.id", ondelete="CASCADE"), nullable=False
    )
    food_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("foods.id", ondelete="SET NULL"), nullable=True
    )
    food_name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    nutrition_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    nutrition_known: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    nutrition_source: Mapped[str | None] = mapped_column(String(160), nullable=True)
    confidence: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)

    meal: Mapped["Meal"] = relationship("Meal", back_populates="items")
    food: Mapped["Food | None"] = relationship("Food", back_populates="items")


class WaterIntake(Base):
    __tablename__ = "water_intakes"
    __table_args__ = (Index("ix_water_user_consumed_at", "user_id", "consumed_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    milliliters: Mapped[float] = mapped_column(Float, nullable=False)
    consumed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="water_intakes")


from app.models.food import Food  # noqa: E402,F401
from app.models.user import User  # noqa: E402,F401

__all__ = ["Meal", "MealItem", "WaterIntake"]
