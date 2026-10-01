def test_meal_parser_does_not_invent_missing_quantities(client):
    response = client.post("/api/ai/analyze-meal", json={"text": "J'ai mangé une salade et du riz."})
    assert response.status_code == 200
    data = response.json()
    assert data["clarification"]
    assert any(item["needs_clarification"] for item in data["items"])


def test_recommendation_and_export(account):
    client, headers = account
    recommendation = client.post("/api/ai/recommendations", headers=headers)
    assert recommendation.status_code == 200
    assert "disclaimer" in recommendation.json()
    suggestion = client.post("/api/ai/meal-suggestions", headers=headers, json={"meal_type": "dinner"})
    assert suggestion.status_code == 200
    assert suggestion.json()["suggestions"]
    export = client.get("/api/users/me/export", headers=headers)
    assert export.status_code == 200
    assert export.json()["profile"]["email"] == "test@example.com"
