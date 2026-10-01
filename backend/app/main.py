"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import init_db
from app.services.seed import seed_demo_foods

settings = get_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("caltracker")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if settings.seed_demo_foods:
        seed_demo_foods()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Suivi nutritionnel privé: les calculs sont déterministes et les fonctions IA sont optionnelles. "
        "L'application ne fournit pas de diagnostic médical."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    response = await call_next(request)
    # Do not log query strings or bodies: they may contain personal data.
    logger.info("%s %s -> %s", request.method, request.url.path, response.status_code)
    return response


@app.exception_handler(Exception)
async def safe_exception_handler(_request: Request, _exc: Exception):
    logger.exception("Unhandled application error")
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur."})


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "caltracker-api", "environment": settings.environment}


@app.get("/privacy", tags=["system"])
def privacy():
    return {
        "title": "Confidentialité",
        "data_collected": ["compte et profil nutritionnel", "repas saisis", "hydratation optionnelle"],
        "purpose": "Calculer des agrégats personnels et personnaliser des explications demandées par l'utilisateur.",
        "sharing": "Les données ne sont pas partagées entre comptes. Un fournisseur IA configuré peut recevoir le contexte minimal nécessaire à une demande IA.",
        "controls": ["export via /api/users/me/export", "suppression via DELETE /api/users/me"],
        "medical_notice": "CalTracker fournit des informations générales et ne remplace pas un médecin ou un diététicien.",
    }


app.include_router(api_router, prefix="/api")
# The unprefixed aliases keep the endpoint names from the product brief
# available to simple integrations; the documented canonical form is /api/.
app.include_router(api_router, include_in_schema=False)
