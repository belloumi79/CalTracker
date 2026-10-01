"""Contracts for provider-agnostic AI features."""

from datetime import date as date_type

from pydantic import BaseModel, Field


class AnalyzeMealRequest(BaseModel):
    text: str = Field(min_length=3, max_length=2000)


class ParsedFoodItem(BaseModel):
    food: str
    quantity: float | None = Field(default=None, gt=0)
    unit: str | None = None
    estimated: bool = False
    confidence: str = "unknown"
    needs_clarification: bool = False


class AnalyzeMealResponse(BaseModel):
    items: list[ParsedFoodItem]
    clarification: str | None = None
    provider: str
    disclaimer: str = "Une quantité manquante ou ambiguë n'est pas inventée silencieusement."


class RecommendationRequest(BaseModel):
    date: date_type | None = None


class RecommendationResponse(BaseModel):
    recommendations: list[str]
    context: dict
    provider: str
    disclaimer: str = (
        "Ces informations sont générales et ne remplacent pas un médecin ou un diététicien."
    )


class MealSuggestionRequest(BaseModel):
    meal_type: str = Field(default="lunch", min_length=2, max_length=24)
    available_ingredients: list[str] = Field(default_factory=list, max_length=50)
    servings: int = Field(default=1, ge=1, le=12)


class MealSuggestion(BaseModel):
    title: str
    ingredients: list[dict]
    nutrition: dict
    estimated: bool = True
    notes: list[str] = Field(default_factory=list)


class MealSuggestionResponse(BaseModel):
    suggestions: list[MealSuggestion]
    provider: str
    disclaimer: str = (
        "Les quantités et valeurs nutritionnelles sont des estimations. Vérifiez les ingrédients et les allergies."
    )


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    provider: str
    disclaimer: str = (
        "L'assistant fournit des informations générales et ne remplace pas un professionnel de santé."
    )
