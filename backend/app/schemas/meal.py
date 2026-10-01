"""Meal and hydration schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MealType = Literal["breakfast", "lunch", "dinner", "snack", "drink", "other"]


class MealItemCreate(BaseModel):
    food_id: str | None = None
    food: str | None = Field(default=None, min_length=1, max_length=160)
    quantity: float = Field(gt=0, le=100000)
    unit: str = Field(min_length=1, max_length=24)

    @field_validator("unit")
    @classmethod
    def clean_unit(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("food")
    @classmethod
    def clean_food(cls, value: str | None) -> str | None:
        return value.strip() if value else value

    @model_validator(mode="after")
    def require_food_reference(self):
        if not self.food_id and not self.food:
            raise ValueError("food_id ou food est requis")
        return self


class MealCreate(BaseModel):
    meal_type: MealType
    eaten_at: datetime | None = None
    description: str | None = Field(default=None, max_length=500)
    items: list[MealItemCreate] | None = Field(default=None, min_length=1, max_length=50)
    # A single-item shorthand keeps the REST endpoint convenient for the
    # example payload in the product brief while ``items`` supports full meals.
    food_id: str | None = None
    food: str | None = Field(default=None, min_length=1, max_length=160)
    quantity: float | None = Field(default=None, gt=0, le=100000)
    unit: str | None = Field(default=None, min_length=1, max_length=24)

    @model_validator(mode="after")
    def normalize_items(self):
        if self.items is None:
            if (not self.food and not self.food_id) or self.quantity is None or not self.unit:
                raise ValueError("items ou le triplet food/quantity/unit est requis")
            self.items = [
                MealItemCreate(
                    food_id=self.food_id,
                    food=self.food,
                    quantity=self.quantity,
                    unit=self.unit,
                )
            ]
        return self


class MealUpdate(BaseModel):
    meal_type: MealType | None = None
    eaten_at: datetime | None = None
    description: str | None = Field(default=None, max_length=500)
    items: list[MealItemCreate] | None = Field(default=None, min_length=1, max_length=50)


class MealItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    food_id: str | None = None
    food_name: str
    quantity: float
    unit: str
    nutrition: dict | None = None
    nutrition_known: bool
    nutrition_source: str | None = None
    confidence: str


class MealRead(BaseModel):
    id: str
    meal_type: MealType
    eaten_at: datetime
    description: str | None = None
    items: list[MealItemRead]
    totals: dict
    has_unknown_nutrition: bool
    created_at: datetime


class WaterIntakeCreate(BaseModel):
    milliliters: float = Field(gt=0, le=20_000)
    consumed_at: datetime | None = None


class WaterIntakeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    milliliters: float
    consumed_at: datetime
