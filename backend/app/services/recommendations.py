"""Hybrid recommendation orchestration: deterministic rules first, AI for language."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.providers import AIProvider, AIProviderError
from app.models.food import Food
from app.models.user import User
from app.nutrition.calculations import (
    add_totals,
    calculate_targets,
    empty_totals,
    normalize_food_name,
    nutrients_for_food,
    rounded_totals,
)
from app.services.analytics import daily_summary


def public_profile(user: User) -> dict[str, Any]:
    """Return only the profile fields required to personalize a response."""

    return {
        "display_name": user.display_name,
        "goals": user.goals or [],
        "dietary_preferences": user.dietary_preferences or [],
        "allergies": user.allergies or [],
        "intolerances": user.intolerances or [],
        "favorite_foods": user.favorite_foods or [],
        "avoid_foods": user.avoid_foods or [],
        "meals_per_day": user.meals_per_day,
        "country": user.country,
        "food_budget": user.food_budget,
        "cultural_constraints": user.cultural_constraints,
    }


def deterministic_recommendations(user: User, summary: dict) -> list[str]:
    """Generate explainable observations; no critical calculation is delegated to AI."""

    consumed = summary["consumed"]
    targets = summary["targets"]
    rules: list[str] = []
    if summary["meal_count"] == 0:
        rules.append("Aucun repas n'est enregistré pour cette journée. Ajoutez vos repas pour obtenir une tendance utile.")
    if summary["unknown_item_count"]:
        rules.append(
            f"{summary['unknown_item_count']} élément(s) n'ont pas de données nutritionnelles compatibles; "
            "les totaux sont donc partiels."
        )
    if targets.get("calories") is not None and consumed["calories"]:
        ratio = consumed["calories"] / targets["calories"]
        if ratio > 1.15:
            rules.append("Les calories enregistrées dépassent l'estimation cible de plus de 15 % aujourd'hui.")
        elif ratio < 0.75:
            rules.append("Les calories enregistrées sont nettement sous l'estimation cible; vérifiez que tous les repas sont saisis.")
    if targets.get("fiber_g") and consumed["fiber_g"] < targets["fiber_g"] * 0.7:
        rules.append("Les fibres semblent faibles sur les données connues; pensez progressivement aux légumes, fruits, légumineuses et céréales complètes.")
    if targets.get("protein_g") and consumed["protein_g"] < targets["protein_g"] * 0.7:
        rules.append("Les protéines connues sont sous l'estimation du jour; répartir des sources adaptées sur les repas peut aider.")
    if consumed["sodium_mg"] > 2300:
        rules.append("Le sodium enregistré est supérieur à une référence générale de 2 300 mg; vérifiez les produits très salés, sans en faire un avis médical.")
    if not rules:
        rules.append("Les données connues de la journée sont cohérentes avec les repères configurés; poursuivez l'enregistrement régulier.")
    return rules


def _context(user: User, summary: dict, rules: list[str]) -> dict[str, Any]:
    return {
        "profile": public_profile(user),
        "summary": {
            "date": str(summary["date"]),
            "consumed": summary["consumed"],
            "targets": summary["targets"],
            "meal_count": summary["meal_count"],
            "unknown_item_count": summary["unknown_item_count"],
        },
        "rules": rules,
    }


async def recommendation_response(db: Session, user: User, provider: AIProvider, day: date) -> dict[str, Any]:
    summary = daily_summary(db, user, day)
    rules = deterministic_recommendations(user, summary)
    try:
        recommendations = await provider.explain_recommendations(_context(user, summary, rules))
    except AIProviderError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {
        "recommendations": recommendations or rules,
        "context": {
            "date": str(day),
            "known_nutrition": summary["known_nutrition"],
            "targets": summary["targets"],
        },
        "provider": provider.name,
    }


def _forbidden(name: str, user: User) -> bool:
    normalized = normalize_food_name(name)
    exclusions = (user.allergies or []) + (user.intolerances or []) + (user.avoid_foods or [])
    return any(normalize_food_name(term) and normalize_food_name(term) in normalized for term in exclusions)


def _find_food(db: Session, name: str) -> Food | None:
    normalized = normalize_food_name(name)
    food = db.scalar(select(Food).where(Food.normalized_name == normalized).limit(1))
    if food:
        return food
    # A modest singular fallback helps natural-language French plurals without
    # pretending it is a semantic food database.
    candidates = [normalized.removesuffix("s"), normalized.removesuffix("es")]
    for candidate in candidates:
        if candidate and candidate != normalized:
            food = db.scalar(select(Food).where(Food.normalized_name == candidate).limit(1))
            if food:
                return food
    return db.scalar(select(Food).where(Food.normalized_name.like(f"{normalized}%")).limit(1))


async def meal_suggestion_response(
    db: Session,
    user: User,
    provider: AIProvider,
    meal_type: str,
    available_ingredients: list[str],
    servings: int,
) -> dict[str, Any]:
    context = {
        "profile": public_profile(user),
        "meal_type": meal_type,
        "available_ingredients": available_ingredients,
        "servings": servings,
        "targets": calculate_targets(user),
    }
    try:
        raw_suggestions = await provider.suggest_meals(context)
    except AIProviderError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    suggestions: list[dict[str, Any]] = []
    for raw in raw_suggestions:
        ingredients = raw.get("ingredients", []) if isinstance(raw, dict) else []
        safe_ingredients = []
        totals: dict[str, float] = empty_totals()
        has_known_nutrition = False
        blocked = False
        for ingredient in ingredients:
            if not isinstance(ingredient, dict) or not ingredient.get("food"):
                continue
            name = str(ingredient["food"])
            if _forbidden(name, user):
                blocked = True
                break
            quantity = ingredient.get("quantity")
            unit = ingredient.get("unit")
            food = _find_food(db, name)
            nutrients = None
            if food and isinstance(quantity, (int, float)) and unit:
                nutrients = nutrients_for_food(food, float(quantity) * servings, str(unit))
            if nutrients:
                add_totals(totals, nutrients)
                has_known_nutrition = True
            safe_ingredients.append(
                {
                    "food": name,
                    "quantity": quantity,
                    "unit": unit,
                    "estimated": True,
                    "nutrition_known": nutrients is not None,
                }
            )
        if blocked or not safe_ingredients:
            continue
        raw_notes = raw.get("notes", []) if isinstance(raw, dict) else []
        suggestions.append(
            {
                "title": str(raw.get("title", "Suggestion de repas")),
                "ingredients": safe_ingredients,
                "nutrition": rounded_totals(totals) if has_known_nutrition else {},
                "estimated": True,
                "notes": [str(note) for note in raw_notes[:5]],
            }
        )
    return {"suggestions": suggestions, "provider": provider.name}


async def chat_response(db: Session, user: User, provider: AIProvider, message: str, day: date) -> dict[str, Any]:
    summary = daily_summary(db, user, day)
    try:
        answer = await provider.chat(message, _context(user, summary, deterministic_recommendations(user, summary)))
    except AIProviderError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {"answer": answer, "provider": provider.name}
