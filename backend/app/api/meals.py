"""Owner-scoped meal and hydration endpoints."""

from datetime import date

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, Database
from app.schemas.auth import MessageResponse
from app.schemas.meal import MealCreate, MealRead, MealUpdate, WaterIntakeCreate, WaterIntakeRead
from app.services.meals import (
    create_meal,
    create_water,
    delete_meal,
    get_meal,
    list_meals,
    meal_to_dict,
    update_meal,
)

router = APIRouter(prefix="/meals", tags=["meals"])


@router.post("", response_model=MealRead, status_code=status.HTTP_201_CREATED)
def add_meal(payload: MealCreate, user: CurrentUser, db: Database):
    return meal_to_dict(create_meal(db, user, payload))


@router.get("", response_model=list[MealRead])
def get_meals(
    user: CurrentUser,
    db: Database,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
):
    return [meal_to_dict(meal) for meal in list_meals(db, user, start_date, end_date)]


@router.get("/{meal_id}", response_model=MealRead)
def read_meal(meal_id: str, user: CurrentUser, db: Database):
    return meal_to_dict(get_meal(db, user, meal_id))


@router.put("/{meal_id}", response_model=MealRead)
def edit_meal(meal_id: str, payload: MealUpdate, user: CurrentUser, db: Database):
    return meal_to_dict(update_meal(db, user, meal_id, payload))


@router.delete("/{meal_id}", response_model=MessageResponse)
def remove_meal(meal_id: str, user: CurrentUser, db: Database):
    delete_meal(db, user, meal_id)
    return {"message": "Repas supprimé."}


water_router = APIRouter(prefix="/water", tags=["water"])


@water_router.post("", response_model=WaterIntakeRead, status_code=status.HTTP_201_CREATED)
def add_water(payload: WaterIntakeCreate, user: CurrentUser, db: Database):
    return create_water(db, user, payload)
