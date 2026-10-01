"""Aggregate versioned API router."""

from fastapi import APIRouter

from app.api.ai import router as ai_router
from app.api.auth import router as auth_router
from app.api.foods import router as foods_router
from app.api.meals import router as meals_router
from app.api.meals import water_router
from app.api.nutrition import router as nutrition_router
from app.api.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(foods_router)
api_router.include_router(meals_router)
api_router.include_router(water_router)
api_router.include_router(nutrition_router)
api_router.include_router(ai_router)
