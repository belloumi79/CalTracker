"""Owner-scoped daily, weekly, and monthly nutrition analytics."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.meal import Meal, WaterIntake
from app.models.user import User
from app.nutrition.calculations import (
    NUTRIENT_KEYS,
    add_totals,
    calculate_targets,
    date_bounds,
    empty_totals,
    macro_distribution,
    rounded_totals,
)
from app.services.meals import meal_totals


def _meals_for_day(db: Session, user_id: str, day: date) -> list[Meal]:
    start, end = date_bounds(day)
    query = (
        select(Meal)
        .where(Meal.user_id == user_id, Meal.eaten_at >= start, Meal.eaten_at < end)
        .options(selectinload(Meal.items))
        .order_by(Meal.eaten_at.asc())
    )
    return list(db.scalars(query).all())


def _water_for_day(db: Session, user_id: str, day: date) -> float:
    start, end = date_bounds(day)
    # Fetch values explicitly rather than relying on a dialect-specific scalar
    # aggregate so the SQLite and PostgreSQL paths behave identically.
    values = db.scalars(
        select(WaterIntake.milliliters).where(
            WaterIntake.user_id == user_id,
            WaterIntake.consumed_at >= start,
            WaterIntake.consumed_at < end,
        )
    ).all()
    return round(sum(values), 1) if values else 0.0


def _consume_day(meals: list[Meal]) -> tuple[dict[str, float], int, int, bool]:
    totals = empty_totals()
    unknown = 0
    for meal in meals:
        meal_values, _known, meal_unknown = meal_totals(meal)
        add_totals(totals, meal_values)
        unknown += meal_unknown
    return rounded_totals(totals), len(meals), unknown, unknown == 0


def _trend(db: Session, user: User, day: date, calories: float, known: bool) -> str:
    if not known or calories <= 0:
        return "insufficient_data"
    previous_meals = _meals_for_day(db, user.id, day - timedelta(days=1))
    previous, _, _, previous_known = _consume_day(previous_meals)
    previous_calories = previous["calories"]
    if not previous_known or previous_calories <= 0:
        return "insufficient_comparison"
    difference = (calories - previous_calories) / previous_calories
    if difference > 0.1:
        return "up"
    if difference < -0.1:
        return "down"
    return "stable"


def daily_summary(db: Session, user: User, day: date) -> dict:
    meals = _meals_for_day(db, user.id, day)
    consumed, meal_count, unknown_count, known = _consume_day(meals)
    targets = calculate_targets(user)
    deviations = {
        key: round(consumed[key] - targets[key], 2) if targets.get(key) is not None else None
        for key in NUTRIENT_KEYS
    }
    return {
        "date": day,
        "consumed": consumed,
        "targets": targets,
        "deviations": deviations,
        "macro_distribution": macro_distribution(consumed),
        "meal_count": meal_count,
        "water_ml": _water_for_day(db, user.id, day),
        "known_nutrition": known,
        "unknown_item_count": unknown_count,
        "trend": _trend(db, user, day, consumed["calories"], known),
    }


def period_summary(db: Session, user: User, start_date: date, end_date: date) -> dict:
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    days = []
    current = start_date
    totals = empty_totals()
    adherence_values: list[float] = []
    targets = calculate_targets(user)
    while current <= end_date:
        summary = daily_summary(db, user, current)
        add_totals(totals, summary["consumed"])
        days.append(
            {
                "date": current,
                "consumed": summary["consumed"],
                "meal_count": summary["meal_count"],
                "water_ml": summary["water_ml"],
                "known_nutrition": summary["known_nutrition"],
            }
        )
        if targets["calories"] and summary["meal_count"] and summary["known_nutrition"]:
            ratio = summary["consumed"]["calories"] / targets["calories"]
            adherence_values.append(1.0 if 0.85 <= ratio <= 1.15 else 0.0)
        current += timedelta(days=1)

    day_count = len(days)
    averages = {key: round(totals[key] / day_count, 2) for key in NUTRIENT_KEYS}
    return {
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "totals": rounded_totals(totals),
        "averages": averages,
        "average_meals": round(sum(day["meal_count"] for day in days) / day_count, 2),
        "goal_adherence": round(sum(adherence_values) / len(adherence_values), 3)
        if adherence_values
        else None,
    }
