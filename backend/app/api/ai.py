"""AI-assisted parsing, recommendations, suggestions, and chat endpoints."""

from datetime import date

from fastapi import APIRouter, HTTPException, status

from app.ai.providers import AIProviderError, make_provider
from app.core.config import get_settings
from app.core.deps import CurrentUser, Database
from app.schemas.ai import (
    AnalyzeMealRequest,
    AnalyzeMealResponse,
    ChatRequest,
    ChatResponse,
    MealSuggestionRequest,
    MealSuggestionResponse,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.recommendations import chat_response, meal_suggestion_response, recommendation_response

router = APIRouter(prefix="/ai", tags=["ai"])


def _provider():
    return make_provider(get_settings())


def _provider_error(exc: AIProviderError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.post("/analyze-meal", response_model=AnalyzeMealResponse)
async def analyze_meal(payload: AnalyzeMealRequest):
    try:
        raw = await _provider().analyze_meal(payload.text)
        return AnalyzeMealResponse.model_validate({**raw, "provider": _provider().name})
    except AIProviderError as exc:
        raise _provider_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Réponse IA non conforme.") from exc


@router.post("/recommendations", response_model=RecommendationResponse)
async def recommendations(
    user: CurrentUser,
    db: Database,
    payload: RecommendationRequest | None = None,
    day: date | None = None,
):
    requested_day = day or (payload.date if payload and payload.date else date.today())
    return await recommendation_response(db, user, _provider(), requested_day)


@router.post("/meal-suggestions", response_model=MealSuggestionResponse)
async def meal_suggestions(payload: MealSuggestionRequest, user: CurrentUser, db: Database):
    return await meal_suggestion_response(
        db,
        user,
        _provider(),
        payload.meal_type,
        payload.available_ingredients,
        payload.servings,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, user: CurrentUser, db: Database):
    return await chat_response(db, user, _provider(), payload.message, date.today())
