"""Profile schemas with conservative validation limits."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Sex = Literal["female", "male", "other", "prefer_not_to_say"]
ActivityLevel = Literal["sedentary", "light", "moderate", "very_active", "athlete"]


def _clean_list(value: list[str] | None) -> list[str] | None:
    if value is None:
        return None
    return list(dict.fromkeys(item.strip() for item in value if item and item.strip()))


class UserProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    age: int | None = Field(default=None, ge=13, le=120)
    sex: Sex | None = None
    height_cm: float | None = Field(default=None, ge=80, le=250)
    weight_kg: float | None = Field(default=None, ge=25, le=500)
    activity_level: ActivityLevel | None = None
    goals: list[str] | None = Field(default=None, max_length=10)
    dietary_preferences: list[str] | None = Field(default=None, max_length=20)
    allergies: list[str] | None = Field(default=None, max_length=30)
    intolerances: list[str] | None = Field(default=None, max_length=30)
    favorite_foods: list[str] | None = Field(default=None, max_length=30)
    avoid_foods: list[str] | None = Field(default=None, max_length=30)
    meals_per_day: int | None = Field(default=None, ge=1, le=12)
    country: str | None = Field(default=None, max_length=100)
    food_budget: float | None = Field(default=None, ge=0, le=1_000_000)
    cultural_constraints: str | None = Field(default=None, max_length=500)
    daily_calorie_target: float | None = Field(default=None, ge=800, le=10_000)

    _normalize_goals = field_validator(
        "goals",
        "dietary_preferences",
        "allergies",
        "intolerances",
        "favorite_foods",
        "avoid_foods",
        mode="before",
    )(_clean_list)

    @field_validator("display_name", "country", "cultural_constraints")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class UserProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    age: int | None = None
    sex: Sex | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    activity_level: ActivityLevel | None = None
    goals: list[str] = Field(default_factory=list)
    dietary_preferences: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    intolerances: list[str] = Field(default_factory=list)
    favorite_foods: list[str] = Field(default_factory=list)
    avoid_foods: list[str] = Field(default_factory=list)
    meals_per_day: int | None = None
    country: str | None = None
    food_budget: float | None = None
    cultural_constraints: str | None = None
    daily_calorie_target: float | None = None
    created_at: datetime
    updated_at: datetime
