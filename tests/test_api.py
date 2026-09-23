from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def recommendation_payload(**overrides):
	payload = {
		"city": "Алматы",
		"date": "2099-01-01",
		"event_type": "корпоратив",
		"category": "Ведущий",
		"budget_kzt": 2_000_000,
		"duration_hours": 4.0,
		"language": "русский",
	}
	payload.update(overrides)
	return payload


def test_health_returns_status_and_loaded_vendor_count():
	response = client.get("/health")

	assert response.status_code == 200
	assert response.json()["status"] == "ok"
	assert response.json()["vendors_loaded"] == 66


def test_recommend_returns_response():
	response = client.post("/recommend", json=recommendation_payload())

	assert response.status_code == 200
	assert "status" in response.json()
	assert "results" in response.json()


def test_category_not_found_works_through_api():
	response = client.post(
		"/recommend",
		json=recommendation_payload(category="Несуществующая категория"),
	)

	assert response.status_code == 200
	assert response.json()["status"] == "category_not_found"
	assert response.json()["results"] == []