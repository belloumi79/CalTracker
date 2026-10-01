"""Provider-agnostic AI contracts and implementations.

The deterministic mock provider makes local development and tests work without
an API key. The OpenAI-compatible provider is intentionally a thin adapter so
switching to another model does not touch the business layer.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.config import Settings


class AIProviderError(RuntimeError):
    """A recoverable provider or response-format error."""


class AIProvider(Protocol):
    name: str

    async def analyze_meal(self, text: str) -> dict[str, Any]: ...

    async def explain_recommendations(self, context: dict[str, Any]) -> list[str]: ...

    async def suggest_meals(self, context: dict[str, Any]) -> list[dict[str, Any]]: ...

    async def chat(self, message: str, context: dict[str, Any]) -> str: ...


@dataclass
class MockAIProvider:
    """Safe offline provider used by default and in automated tests."""

    name: str = "mock"

    _number_words = {
        "un": 1,
        "une": 1,
        "un(e)": 1,
        "deux": 2,
        "trois": 3,
        "quatre": 4,
        "cinq": 5,
        "six": 6,
        "sept": 7,
        "huit": 8,
        "neuf": 9,
        "dix": 10,
        "half": 0.5,
        "demi": 0.5,
        "moitie": 0.5,
    }
    _unit_words = (
        "kg",
        "g",
        "grammes?",
        "ml",
        "l",
        "pieces?",
        "unit(?:e|és|es)?",
        "portions?",
        "servings?",
        "cuiller(?:e|es)",
    )

    async def analyze_meal(self, text: str) -> dict[str, Any]:
        cleaned = re.sub(r"^[^:]{0,40}:\s*", "", text.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(
            r"^(?:j['’]?(?:ai|a)|je viens de|i just|i ate|i had)\s+(?:mangé|mange|eaten|ate|had)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        # Commas and conjunctions separate food mentions for common French and English phrasing.
        parts = [part.strip(" .") for part in re.split(r"\s*(?:,|;|\bet\b|\band\b|\bpuis\b)\s*", cleaned, flags=re.I)]
        parts = [part for part in parts if part]
        parsed: list[dict[str, Any]] = []
        for part in parts:
            item = self._parse_part(part)
            if item:
                parsed.append(item)

        if not parsed:
            return {
                "items": [],
                "clarification": "Je n'ai pas reconnu d'aliment. Indiquez par exemple « 150 g de riz ». ",
            }
        ambiguous = [item["food"] for item in parsed if item["needs_clarification"]]
        return {
            "items": parsed,
            "clarification": (
                "Quelle quantité approximative pour : " + ", ".join(ambiguous) + " ?"
                if ambiguous
                else None
            ),
        }

    def _parse_part(self, part: str) -> dict[str, Any] | None:
        part = re.sub(r"^(?:et|also|avec|with)\s+", "", part, flags=re.I).strip()
        numeric = re.match(
            r"^(?P<quantity>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|g|ml|l|pieces?|units?|portions?|servings?|cuill(?:e|ère|eres|ères)s?)?\s*(?:de|du|des|d['’]|of)?\s*(?P<food>.+)$",
            part,
            flags=re.I,
        )
        if numeric:
            quantity = float(numeric.group("quantity").replace(",", "."))
            raw_unit = (numeric.group("unit") or "piece").lower()
            food = self._clean_food(numeric.group("food"))
            return {
                "food": food,
                "quantity": quantity,
                "unit": self._normalize_unit(raw_unit),
                "estimated": False,
                "confidence": "explicit",
                "needs_clarification": False,
            }

        words = re.match(
            r"^(?P<quantity>un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|demi(?:e)?|half)\s+(?:(?P<unit>pieces?|unit(?:e|és|es)?|portions?|servings?)\s+(?:de|of)?\s+)?(?P<food>.+)$",
            part,
            flags=re.I,
        )
        if words:
            quantity = float(self._number_words[words.group("quantity").casefold().replace("é", "e")])
            raw_unit = words.group("unit") or "piece"
            return {
                "food": self._clean_food(words.group("food")),
                "quantity": quantity,
                "unit": self._normalize_unit(raw_unit),
                "estimated": False,
                "confidence": "explicit",
                "needs_clarification": False,
            }

        trailing = re.match(
            r"^(?P<food>.+?)\s+(?P<quantity>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|g|ml|l)$",
            part,
            flags=re.I,
        )
        if trailing:
            return {
                "food": self._clean_food(trailing.group("food")),
                "quantity": float(trailing.group("quantity").replace(",", ".")),
                "unit": self._normalize_unit(trailing.group("unit")),
                "estimated": False,
                "confidence": "explicit",
                "needs_clarification": False,
            }

        food = self._clean_food(part)
        if not food:
            return None
        return {
            "food": food,
            "quantity": None,
            "unit": None,
            "estimated": False,
            "confidence": "unknown",
            "needs_clarification": True,
        }

    @staticmethod
    def _clean_food(value: str) -> str:
        value = re.sub(r"\b(?:j['’]ai|mangé|mange|de|du|des|of|a|an|the)\b", " ", value, flags=re.I)
        value = re.sub(r"\s+", " ", value).strip(" .!?'")
        return value

    @staticmethod
    def _normalize_unit(value: str) -> str:
        value = value.casefold()
        if value.startswith("gram"):
            return "g"
        if value.startswith("piece") or value.startswith("unit"):
            return "piece"
        if value.startswith("portion") or value.startswith("serv"):
            return "portion"
        if value.startswith("cuill"):
            return "portion"
        return value

    async def explain_recommendations(self, context: dict[str, Any]) -> list[str]:
        rules = context.get("rules", [])
        if rules:
            return list(rules)
        return ["Enregistrez quelques repas pour obtenir des observations personnalisées."]

    async def suggest_meals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        meal_type = context.get("meal_type", "lunch")
        preferences = " ".join(context.get("preferences", []))
        if any(term in preferences.casefold() for term in ("vegetarian", "végétarien", "vegan", "végane")):
            title = "Bol de lentilles, riz et légumes"
            ingredients = [
                {"food": "lentilles cuites", "quantity": 150, "unit": "g", "estimated": True},
                {"food": "riz cuit", "quantity": 120, "unit": "g", "estimated": True},
                {"food": "légumes de saison", "quantity": 200, "unit": "g", "estimated": True},
            ]
        else:
            title = f"Assiette équilibrée pour {meal_type}"
            ingredients = [
                {"food": "poulet grillé", "quantity": 120, "unit": "g", "estimated": True},
                {"food": "riz cuit", "quantity": 150, "unit": "g", "estimated": True},
                {"food": "légumes de saison", "quantity": 200, "unit": "g", "estimated": True},
            ]
        return [
            {
                "title": title,
                "ingredients": ingredients,
                "nutrition": {},
                "estimated": True,
                "notes": ["Adaptez les quantités à votre faim et vérifiez les ingrédients exclus."],
            }
        ]

    async def chat(self, message: str, context: dict[str, Any]) -> str:
        lowered = message.casefold()
        if any(term in lowered for term in ("douleur", "malaise", "symptôme", "allergique", "urgence")):
            return (
                "Je ne peux pas évaluer une situation médicale. En cas de réaction importante ou d'urgence, "
                "contactez immédiatement les services d'urgence ou un professionnel de santé."
            )
        if "analyse" in lowered or "journée" in lowered or "journee" in lowered:
            summary = context.get("summary", {})
            consumed = summary.get("consumed", {})
            return (
                f"Aujourd'hui, les données enregistrées indiquent environ {consumed.get('calories', 0):.0f} kcal "
                "connues. Les éléments sans données fiables ne sont pas estimés automatiquement. "
                "Je peux proposer une piste générale, mais cela ne remplace pas un professionnel."
            )
        return (
            "Je peux analyser les repas enregistrés, expliquer les tendances ou proposer une idée de repas. "
            "Indiquez vos contraintes et n'oubliez pas que ces informations sont générales."
        )


@dataclass
class OpenAIProvider:
    """OpenAI-compatible adapter; all prompts receive only the required context."""

    api_key: str
    model: str
    base_url: str
    timeout: float = 20.0
    name: str = "openai"

    async def _json_call(self, system: str, user: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                result = json.loads(content)
                if not isinstance(result, dict):
                    raise ValueError("Provider response is not an object")
                return result
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AIProviderError("Le fournisseur IA est momentanément indisponible.") from exc

    async def analyze_meal(self, text: str) -> dict[str, Any]:
        return await self._json_call(
            "Transform meal text into JSON {items:[{food,quantity,unit,estimated,confidence,needs_clarification}],clarification}. Never invent a missing quantity.",
            text,
        )

    async def explain_recommendations(self, context: dict[str, Any]) -> list[str]:
        result = await self._json_call(
            "Return JSON {recommendations:[string]}. Be cautious, explain uncertainty, and never provide a medical diagnosis.",
            json.dumps(context, ensure_ascii=False),
        )
        values = result.get("recommendations", [])
        return [str(value) for value in values[:8]] if isinstance(values, list) else []

    async def suggest_meals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        result = await self._json_call(
            "Return JSON {suggestions:[{title,ingredients,nutrition,estimated,notes}]}. Respect exclusions and mark estimates.",
            json.dumps(context, ensure_ascii=False),
        )
        values = result.get("suggestions", [])
        return values[:5] if isinstance(values, list) else []

    async def chat(self, message: str, context: dict[str, Any]) -> str:
        result = await self._json_call(
            "Return JSON {answer:string}. Do not diagnose; suggest a healthcare professional for medical situations.",
            json.dumps({"message": message, "context": context}, ensure_ascii=False),
        )
        return str(result.get("answer", "Je ne peux pas répondre pour le moment."))


def make_provider(settings: Settings) -> AIProvider:
    """Select a provider without coupling API routes to a vendor SDK."""

    if settings.ai_provider == "openai" and settings.openai_api_key:
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
            timeout=settings.ai_timeout_seconds,
        )
    return MockAIProvider()
