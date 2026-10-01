
from app.models.user import User
from app.nutrition.calculations import calculate_targets


def test_food_scaling_uses_declared_basis(account):
    client, headers = account
    foods = client.get("/api/foods").json()["items"]
    rice = next(food for food in foods if food["name"] == "Riz cuit")
    meal = client.post(
        "/api/meals",
        headers=headers,
        json={"meal_type": "lunch", "food_id": rice["id"], "quantity": 150, "unit": "g"},
    )
    # The shorthand payload is deliberately supported by the API.
    assert meal.status_code == 201
    assert meal.json()["totals"]["calories"] == 195.0


def test_daily_and_period_aggregates(account):
    client, headers = account
    foods = client.get("/api/foods").json()["items"]
    apple = next(food for food in foods if food["name"] == "Pomme")
    for quantity in (100, 200):
        assert client.post(
            "/api/meals",
            headers=headers,
            json={"meal_type": "snack", "food_id": apple["id"], "quantity": quantity, "unit": "g"},
        ).status_code == 201
    daily = client.get("/api/nutrition/daily", headers=headers).json()
    assert daily["consumed"]["calories"] == 156.0
    assert daily["meal_count"] == 2
    weekly = client.get("/api/nutrition/weekly", headers=headers)
    assert weekly.status_code == 200
    assert len(weekly.json()["days"]) == 7


def test_unknown_unit_is_explicitly_partial(account):
    client, headers = account
    foods = client.get("/api/foods").json()["items"]
    rice = next(food for food in foods if food["name"] == "Riz cuit")
    meal = client.post(
        "/api/meals",
        headers=headers,
        json={"meal_type": "dinner", "food_id": rice["id"], "quantity": 1, "unit": "portion"},
    )
    assert meal.status_code == 201
    assert meal.json()["has_unknown_nutrition"] is True
    summary = client.get("/api/nutrition/daily", headers=headers).json()
    assert summary["unknown_item_count"] == 1
    assert summary["known_nutrition"] is False


def test_target_calculation_is_transparent():
    user = User(
        display_name="Target",
        email="target@example.com",
        password_hash="not-used",
        age=30,
        sex="female",
        height_cm=165,
        weight_kg=65,
        activity_level="moderate",
        goals=["maintien du poids"],
    )
    targets = calculate_targets(user)
    assert targets["basis"] == "mifflin_st_jeor_estimate"
    assert targets["estimated"] is True
    assert targets["calories"] > 0
