"""Meal catalog resolution and owner-scoped CRUD."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.food import Food
from app.models.meal import Meal, MealItem, WaterIntake
from app.models.user import User
from app.nutrition.calculations import (
    normalize_food_name,
    nutrients_for_food,
    rounded_totals,
    to_naive_utc,
)
from app.schemas.meal import MealCreate, MealItemCreate, MealUpdate, WaterIntakeCreate


def _resolve_food(db: Session, item: MealItemCreate) -> Food | None:
    if item.food_id:
        food = db.get(Food, item.food_id)
        if food is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aliment introuvable.")
        return food
    if not item.food:
        return None
    normalized = normalize_food_name(item.food)
    food = db.scalar(select(Food).where(Food.normalized_name == normalized).limit(1))
    if food:
        return food
    # Natural-language parsing often produces a generic name ("riz") or a
    # French plural ("oeufs"). Only use an explicit catalog prefix/singular
    # match; otherwise preserve the item as nutrition-unknown.
    candidates = [normalized.removesuffix("s"), normalized.removesuffix("es")]
    for candidate in candidates:
        if candidate and candidate != normalized:
            food = db.scalar(select(Food).where(Food.normalized_name == candidate).limit(1))
            if food:
                return food
    return db.scalar(select(Food).where(Food.normalized_name.like(f"{normalized}%")).limit(1))


def _build_item(db: Session, item: MealItemCreate) -> MealItem:
    food = _resolve_food(db, item)
    food_name = food.name if food else (item.food or "Aliment inconnu")
    snapshot = nutrients_for_food(food, item.quantity, item.unit) if food else None
    return MealItem(
        food_id=food.id if food else None,
        food_name=food_name,
        quantity=item.quantity,
        unit=item.unit,
        nutrition_snapshot=snapshot,
        nutrition_known=snapshot is not None,
        nutrition_source=food.source if food else None,
        confidence=food.confidence if food else "unknown",
    )


def _meal_query(user_id: str):
    return (
        select(Meal)
        .where(Meal.user_id == user_id)
        .options(selectinload(Meal.items))
        .order_by(Meal.eaten_at.desc())
    )


def get_meal(db: Session, user: User, meal_id: str) -> Meal:
    meal = db.scalar(_meal_query(user.id).where(Meal.id == meal_id))
    if meal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repas introuvable.")
    return meal


def create_meal(db: Session, user: User, payload: MealCreate) -> Meal:
    meal = Meal(
        user_id=user.id,
        meal_type=payload.meal_type,
        eaten_at=to_naive_utc(payload.eaten_at),
        description=payload.description.strip() if payload.description else None,
    )
    meal.items = [_build_item(db, item) for item in payload.items]
    db.add(meal)
    db.commit()
    return get_meal(db, user, meal.id)


def update_meal(db: Session, user: User, meal_id: str, payload: MealUpdate) -> Meal:
    meal = get_meal(db, user, meal_id)
    data = payload.model_dump(exclude_unset=True)
    if "meal_type" in data and data["meal_type"] is not None:
        meal.meal_type = data["meal_type"]
    if "eaten_at" in data and data["eaten_at"] is not None:
        meal.eaten_at = to_naive_utc(data["eaten_at"])
    if "description" in data:
        meal.description = data["description"].strip() if data["description"] else None
    if payload.items is not None:
        meal.items.clear()
        meal.items.extend(_build_item(db, item) for item in payload.items)
    db.add(meal)
    db.commit()
    return get_meal(db, user, meal.id)


def delete_meal(db: Session, user: User, meal_id: str) -> None:
    meal = get_meal(db, user, meal_id)
    db.delete(meal)
    db.commit()


def list_meals(
    db: Session,
    user: User,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Meal]:
    query = _meal_query(user.id)
    if start_date:
        query = query.where(Meal.eaten_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        # Date filters are inclusive for API callers.
        query = query.where(Meal.eaten_at < datetime.combine(end_date + timedelta(days=1), datetime.min.time()))
    return list(db.scalars(query).all())


def meal_totals(meal: Meal) -> tuple[dict[str, float], bool, int]:
    from app.nutrition.calculations import add_totals, empty_totals

    totals = empty_totals()
    unknown = 0
    for item in meal.items:
        if item.nutrition_known and item.nutrition_snapshot:
            add_totals(totals, item.nutrition_snapshot)
        else:
            unknown += 1
    return rounded_totals(totals), unknown == 0, unknown


def meal_to_dict(meal: Meal) -> dict:
    totals, known, unknown = meal_totals(meal)
    return {
        "id": meal.id,
        "meal_type": meal.meal_type,
        "eaten_at": meal.eaten_at,
        "description": meal.description,
        "items": [
            {
                "id": item.id,
                "food_id": item.food_id,
                "food_name": item.food_name,
                "quantity": item.quantity,
                "unit": item.unit,
                "nutrition": item.nutrition_snapshot,
                "nutrition_known": item.nutrition_known,
                "nutrition_source": item.nutrition_source,
                "confidence": item.confidence,
            }
            for item in meal.items
        ],
        "totals": totals,
        "has_unknown_nutrition": not known,
        "created_at": meal.created_at,
    }


def create_water(db: Session, user: User, payload: WaterIntakeCreate) -> WaterIntake:
    water = WaterIntake(
        user_id=user.id,
        milliliters=payload.milliliters,
        consumed_at=to_naive_utc(payload.consumed_at),
    )
    db.add(water)
    db.commit()
    db.refresh(water)
    return water
