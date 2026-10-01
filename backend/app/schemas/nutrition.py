"""Nutrition analytics response schemas."""

from datetime import date

from pydantic import BaseModel, Field


class NutrientTotals(BaseModel):
    calories: float = 0
    protein_g: float = 0
    carbohydrates_g: float = 0
    fat_g: float = 0
    fiber_g: float = 0
    sugar_g: float = 0
    sodium_mg: float = 0


class TargetValues(BaseModel):
    calories: float | None = None
    protein_g: float | None = None
    carbohydrates_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    sugar_g: float | None = None
    sodium_mg: float | None = None
    basis: str = "insufficient_profile_data"
    estimated: bool = True


class DailySummary(BaseModel):
    date: date
    consumed: NutrientTotals
    targets: TargetValues
    deviations: dict[str, float | None]
    macro_distribution: dict[str, float]
    meal_count: int
    water_ml: float
    known_nutrition: bool
    unknown_item_count: int
    trend: str
    disclaimer: str = (
        "Les valeurs sont des estimations basées sur les données disponibles et ne constituent pas un avis médical."
    )


class PeriodDay(BaseModel):
    date: date
    consumed: NutrientTotals
    meal_count: int
    water_ml: float
    known_nutrition: bool


class PeriodSummary(BaseModel):
    start_date: date
    end_date: date
    days: list[PeriodDay]
    totals: NutrientTotals
    averages: NutrientTotals
    average_meals: float
    goal_adherence: float | None = Field(default=None, description="Internal descriptive ratio, not a medical score")
    disclaimer: str = (
        "Les tendances ne sont fiables que si les repas sont enregistrés de façon suffisamment régulière."
    )
