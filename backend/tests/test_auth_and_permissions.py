def test_register_login_and_profile(account):
    client, headers = account
    profile = client.get("/api/users/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["email"] == "test@example.com"

    updated = client.put(
        "/api/users/me",
        headers=headers,
        json={
            "age": 30,
            "sex": "female",
            "height_cm": 165,
            "weight_kg": 65,
            "activity_level": "moderate",
            "goals": ["maintien du poids"],
            "allergies": ["arachide"],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["age"] == 30
    assert updated.json()["allergies"] == ["arachide"]


def test_duplicate_and_bad_login_are_rejected(client):
    payload = {"email": "same@example.com", "password": "strong-password", "display_name": "Same"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409
    assert client.post("/api/auth/login", json={"email": payload["email"], "password": "wrong"}).status_code == 401


def test_meals_are_isolated_between_users(account, client):
    first_client, first_headers = account
    foods = first_client.get("/api/foods").json()["items"]
    rice = next(food for food in foods if food["name"] == "Riz cuit")
    created = first_client.post(
        "/api/meals",
        headers=first_headers,
        json={"meal_type": "lunch", "items": [{"food_id": rice["id"], "quantity": 100, "unit": "g"}]},
    )
    assert created.status_code == 201

    second = client.post(
        "/api/auth/register",
        json={"email": "other@example.com", "password": "strong-password", "display_name": "Other"},
    )
    assert second.status_code == 201
    login = client.post("/api/auth/login", json={"email": "other@example.com", "password": "strong-password"})
    second_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/meals", headers=second_headers).json() == []
    assert client.get(f"/api/meals/{created.json()['id']}", headers=second_headers).status_code == 404


def test_validation_and_authentication(client):
    assert client.get("/api/users/me").status_code == 401
    invalid = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "short", "display_name": ""},
    )
    assert invalid.status_code == 422
