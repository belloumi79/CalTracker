"""User and nutrition profile persistence model."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import Base, new_id


class User(Base):
    """A private account and its nutrition profile.

    JSON columns hold optional profile lists so the schema can evolve without
    forcing a migration for every new preference category. They are never
    exposed to another user because every protected query is owner-scoped.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(32), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    activity_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    goals: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    dietary_preferences: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    allergies: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    intolerances: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    favorite_foods: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    avoid_foods: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    meals_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    food_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    cultural_constraints: Mapped[str | None] = mapped_column(Text, nullable=True)
    daily_calorie_target: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    meals: Mapped[list["Meal"]] = relationship(
        "Meal", back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    water_intakes: Mapped[list["WaterIntake"]] = relationship(
        "WaterIntake", back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


# Relationship annotations above are resolved after importing app.models.meal.
from app.models.meal import Meal, WaterIntake  # noqa: E402,F401

__all__ = ["User"]
