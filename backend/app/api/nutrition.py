"""Nutrition analytics endpoints."""

from datetime import date, timedelta

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, Database
from app.schemas.nutrition import DailySummary, PeriodSummary
from app.services.analytics import daily_summary, period_summary

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


def _today(value: date | None) -> date:
    return value or date.today()


@router.get("/daily", response_model=DailySummary)
def get_daily(
    user: CurrentUser,
    db: Database,
    day: date | None = Query(default=None, description="Date ISO, par défaut aujourd'hui"),
):
    return daily_summary(db, user, _today(day))


@router.get("/weekly", response_model=PeriodSummary)
def get_weekly(
    user: CurrentUser,
    db: Database,
    end_date: date | None = Query(default=None),
):
    end = _today(end_date)
    return period_summary(db, user, end - timedelta(days=6), end)


@router.get("/monthly", response_model=PeriodSummary)
def get_monthly(
    user: CurrentUser,
    db: Database,
    end_date: date | None = Query(default=None),
):
    end = _today(end_date)
    return period_summary(db, user, end - timedelta(days=29), end)
