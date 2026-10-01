"""Food catalog schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FoodCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    source: str = Field(min_length=1, max_length=160)
    confidence: str = Field(default="unknown", max_length=32)
    basis_quantity: float = Field(default=100, gt=0, le=10000)
    basis_unit: str = Field(default="g", min_length=1, max_length=24)
    calories: float | None = Field(default=None, ge=0, le=10000)
    protein_g: float | None = Field(default=None, ge=0, le=1000)
    carbohydrates_g: float | None = Field(default=None, ge=0, le=1000)
    fat_g: float | None = Field(default=None, ge=0, le=1000)
    fiber_g: float | None = Field(default=None, ge=0, le=1000)
    sugar_g: float | None = Field(default=None, ge=0, le=1000)
    sodium_mg: float | None = Field(default=None, ge=0, le=100000)
    vitamins: dict = Field(default_factory=dict)
    minerals: dict = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=1000)
    is_verified: bool = False


class FoodRead(FoodCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    normalized_name: str
    created_at: datetime


class FoodListResponse(BaseModel):
    items: list[FoodRead]
    total: int
    limit: int
    offset: int
