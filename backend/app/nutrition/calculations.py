"""Deterministic nutrition calculations.

This module intentionally contains no LLM calls. Quantities are converted only
when the unit is compatible with the food's declared nutrition basis; otherwise
an item remains unknown instead of receiving a fabricated estimate.
"""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from app.models.food import Food
from app.models.user import User

NUTRIENT_KEYS = (
    "calories",
    "protein_g",
    "carbohydrates_g",
    "fat_g",
    "fiber_g",
    "sugar_g",
    "sodium_mg",
)

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "very_active": 1.725,
    "athlete": 1.9,
}


def normalize_food_name(value: str) -> str:
    """Normalize accents, punctuation, and whitespace for catalog lookup."""

    value = unicodedata.normalize("NFKD", value)
    value = "".join(character for character in value if not unicodedata.combining(character))
    # NFKD does not decompose every ligature used in food names.
    value = value.replace("œ", "oe").replace("Œ", "OE").replace("æ", "ae").replace("Æ", "AE")
    value = value.casefold()
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def empty_totals() -> dict[str, float]:
    return {key: 0.0 for key in NUTRIENT_KEYS}


def clean_number(value: float | int | None) -> float | None:
    if value is None or not math.isfinite(float(value)):
        return None
    return round(float(value), 2)


def _unit_group(unit: str) -> str:
    unit = normalize_food_name(unit).replace(" ", "")
    aliases = {
        "g": "g",
        "gram": "g",
        "grams": "g",
        "gramme": "g",
        "grammes": "g",
        "kg": "kg",
        "kilogram": "kg",
        "kilograms": "kg",
        "kilogramme": "kg",
        "mg": "mg",
        "milligram": "mg",
        "ml": "ml",
        "milliliter": "ml",
        "milliliters": "ml",
        "millilitre": "ml",
        "millilitres": "ml",
        "l": "l",
        "liter": "l",
        "litre": "l",
        "piece": "piece",
        "pieces": "piece",
        "piece(s)": "piece",
        "unite": "piece",
        "unites": "piece",
        "unit": "piece",
        "units": "piece",
        "œuf": "piece",
        "oeuf": "piece",
        "portion": "portion",
        "portions": "portion",
        "serving": "portion",
        "servings": "portion",
        "part": "portion",
        "parts": "portion",
        "cuillere": "portion",
        "cuilleres": "portion",
        "tablespoon": "portion",
        "tablespoons": "portion",
        "tbsp": "portion",
    }
    return aliases.get(unit, unit)


def _quantity_in_basis(quantity: float, unit: str, basis_quantity: float, basis_unit: str) -> float | None:
    """Convert a quantity to multiples of a food's declared basis."""

    source = _unit_group(unit)
    basis = _unit_group(basis_unit)
    if quantity <= 0 or basis_quantity <= 0:
        return None
    if source == basis:
        return quantity / basis_quantity
    if basis == "g":
        if source == "kg":
            return quantity * 1000 / basis_quantity
        if source == "mg":
            return quantity / 1000 / basis_quantity
    if basis == "kg" and source == "g":
        return quantity / 1000 / basis_quantity
    if basis == "ml":
        if source == "l":
            return quantity * 1000 / basis_quantity
    if basis == "l" and source == "ml":
        return quantity / 1000 / basis_quantity
    # A piece/portion cannot be converted to grams without a declared weight.
    return None


def nutrients_for_food(food: Food, quantity: float, unit: str) -> dict[str, float] | None:
    """Scale a catalog entry, returning ``None`` when the unit is ambiguous."""

    factor = _quantity_in_basis(quantity, unit, food.basis_quantity, food.basis_unit)
    if factor is None:
        return None
    source_values = {
        "calories": food.calories,
        "protein_g": food.protein_g,
        "carbohydrates_g": food.carbohydrates_g,
        "fat_g": food.fat_g,
        "fiber_g": food.fiber_g,
        "sugar_g": food.sugar_g,
        "sodium_mg": food.sodium_mg,
    }
    if not any(value is not None for value in source_values.values()):
        return None
    return {
        key: clean_number(value * factor) for key, value in source_values.items() if value is not None
    }


def add_totals(target: dict[str, float], values: dict[str, Any] | None) -> None:
    """Add known values to totals, ignoring unavailable nutrients."""

    if not values:
        return
    for key in NUTRIENT_KEYS:
        value = values.get(key)
        if value is not None:
            target[key] += float(value)


def rounded_totals(values: dict[str, float]) -> dict[str, float]:
    return {key: round(float(values.get(key, 0.0)), 2) for key in NUTRIENT_KEYS}


def macro_distribution(totals: dict[str, float]) -> dict[str, float]:
    """Return energy percentages for the three macros when energy is available."""

    energy = (
        totals.get("protein_g", 0) * 4
        + totals.get("carbohydrates_g", 0) * 4
        + totals.get("fat_g", 0) * 9
    )
    if energy <= 0:
        return {"protein_percent": 0.0, "carbohydrates_percent": 0.0, "fat_percent": 0.0}
    return {
        "protein_percent": round(totals.get("protein_g", 0) * 4 / energy * 100, 1),
        "carbohydrates_percent": round(totals.get("carbohydrates_g", 0) * 4 / energy * 100, 1),
        "fat_percent": round(totals.get("fat_g", 0) * 9 / energy * 100, 1),
    }


def calculate_targets(user: User) -> dict[str, Any]:
    """Estimate daily targets from profile data using transparent heuristics.

    The values are educational estimates, not prescriptions. An explicitly
    supplied calorie target wins over the estimate; all other values remain
    marked as estimated so the UI can communicate uncertainty.
    """

    calorie_target = user.daily_calorie_target
    basis = "user_defined" if calorie_target is not None else "insufficient_profile_data"
    estimated = calorie_target is None

    if calorie_target is None and user.age and user.height_cm and user.weight_kg and user.activity_level:
        offset = {"male": 5, "female": -161, "other": -78, "prefer_not_to_say": -78}.get(user.sex or "", -78)
        bmr = 10 * user.weight_kg + 6.25 * user.height_cm - 5 * user.age + offset
        calorie_target = bmr * ACTIVITY_FACTORS[user.activity_level]
        goals = " ".join(user.goals or []).casefold()
        if any(term in goals for term in ("loss", "reduction", "perte", "minceur", "weight_loss")):
            calorie_target -= 400
        elif any(term in goals for term in ("gain", "masse", "muscle", "prise")):
            calorie_target += 250
        calorie_target = max(1200.0, round(calorie_target, 0))
        basis = "mifflin_st_jeor_estimate"

    if calorie_target is None:
        return {
            "calories": None,
            "protein_g": None,
            "carbohydrates_g": None,
            "fat_g": None,
            "fiber_g": None,
            "sugar_g": None,
            "sodium_mg": None,
            "basis": basis,
            "estimated": True,
        }

    weight = user.weight_kg or 0
    protein = max(0.8 * weight, calorie_target * 0.20 / 4) if weight else calorie_target * 0.20 / 4
    fat = calorie_target * 0.30 / 9
    carbs = max(0.0, (calorie_target - protein * 4 - fat * 9) / 4)
    return {
        "calories": round(calorie_target, 1),
        "protein_g": round(protein, 1),
        "carbohydrates_g": round(carbs, 1),
        "fat_g": round(fat, 1),
        "fiber_g": 25.0,
        "sugar_g": 50.0,
        "sodium_mg": 2300.0,
        "basis": basis,
        "estimated": estimated,
    }


def to_naive_utc(value: datetime | None) -> datetime:
    """Normalize API timestamps for the timezone-naive DB representation."""

    if value is None:
        return datetime.utcnow()
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def date_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min)
    return start, start + timedelta(days=1)
