from datetime import date

from app.recommender import recommend
from app.scoring import score_vendor
from app.schemas import RecommendationRequest, Vendor


def make_vendor(identifier="vendor-1", **overrides):
	values = {
		"id": identifier,
		"anon_name": identifier,
		"categories": ["Ведущий"],
		"city": "Алматы",
		"city_imputed": False,
		"synthetic": False,
		"price_from_kzt": 100_000,
		"price_imputed": False,
		"event_formats": ["корпоратив"],
		"languages": ["русский"],
		"max_hours": 6.0,
		"busy_dates": set(),
		"description": "корпоратив ведущий",
	}
	values.update(overrides)
	return Vendor(**values)


def make_request(**overrides):
	values = {
		"city": "Алматы",
		"date": date(2026, 9, 23),
		"event_type": "корпоратив",
		"category": "Ведущий",
		"budget_kzt": 200_000,
		"duration_hours": 4.0,
		"language": "русский",
	}
	values.update(overrides)
	return RecommendationRequest(**values)


def test_scoring_is_deterministic():
	vendor = make_vendor()
	request = make_request()

	assert score_vendor(vendor, request) == score_vendor(vendor, request)


def test_same_request_repeated_100_times_has_same_order():
	vendors = [
		make_vendor("b", price_from_kzt=100_000),
		make_vendor("a", price_from_kzt=150_000),
		make_vendor("c", price_from_kzt=180_000),
	]
	request = make_request()

	orders = {
		tuple(card.id for card in recommend(vendors, request).results)
		for _ in range(100)
	}

	assert len(orders) == 1


def test_language_changes_score_but_not_eligibility():
	vendor = make_vendor(languages=["английский"])
	request = make_request(language="русский")

	score = score_vendor(vendor, request)
	response = recommend([vendor], request)

	assert score["language"] < 0.5
	assert response.status == "matched"


def test_higher_total_score_is_sorted_first():
	strong = make_vendor("strong", description="корпоратив ведущий", languages=["русский"])
	weak = make_vendor("weak", description="другое", languages=["английский"])
	request = make_request()

	assert score_vendor(strong, request)["total"] > score_vendor(weak, request)["total"]
	assert [card.id for card in recommend([weak, strong], request).results] == [
		"strong", "weak"
	]


def test_tie_breaking_uses_price_then_id(monkeypatch):
	from app import recommender

	def equal_score(vendor, request):
		return {
			"budget": 0.5,
			"language": 0.5,
			"duration": 0.5,
			"description": 0.5,
			"total": 0.5,
		}

	monkeypatch.setattr(recommender, "score_vendor", equal_score)
	request = make_request()
	vendors = [
		make_vendor("z", price_from_kzt=100_000),
		make_vendor("a", price_from_kzt=150_000),
		make_vendor("b", price_from_kzt=100_000),
	]

	response = recommend(vendors, request)

	assert [card.id for card in response.results] == ["b", "z", "a"]