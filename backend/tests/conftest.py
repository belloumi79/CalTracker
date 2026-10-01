"""Shared API test fixtures."""

import os

# Configure before importing app modules because the engine is created once.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_caltracker.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-bytes")
os.environ.setdefault("SEED_DEMO_FOODS", "true")

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def account(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "strong-password", "display_name": "Test"},
    )
    assert response.status_code == 201
    login = client.post(
        "/api/auth/login", json={"email": "test@example.com", "password": "strong-password"}
    )
    assert login.status_code == 200
    return client, {"Authorization": f"Bearer {login.json()['access_token']}"}
