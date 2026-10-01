"""Read-only food catalog endpoints."""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.deps import Database
from app.models.food import Food
from app.nutrition.calculations import normalize_food_name
from app.schemas.food import FoodListResponse, FoodRead

router = APIRouter(prefix="/foods", tags=["foods"])


@router.get("", response_model=FoodListResponse)
def list_foods(
    db: Database,
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = select(Food)
    count_query = select(func.count(Food.id))
    if search:
        pattern = f"%{normalize_food_name(search)}%"
        query = query.where(Food.normalized_name.ilike(pattern))
        count_query = count_query.where(Food.normalized_name.ilike(pattern))
    items = list(db.scalars(query.order_by(Food.name).offset(offset).limit(limit)).all())
    return {"items": items, "total": int(db.scalar(count_query) or 0), "limit": limit, "offset": offset}


@router.get("/{food_id}", response_model=FoodRead)
def get_food(food_id: str, db: Database):
    food = db.get(Food, food_id)
    if food is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aliment introuvable.")
    return food
