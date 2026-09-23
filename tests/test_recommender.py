from datetime import date

from app.recommender import recommend
from app.schemas import RecommendationRequest, Vendor


REQUEST_DATE = date(2026, 9, 23)


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
		"description": "Test vendor",
	}
	values.update(overrides)
	return Vendor(**values)


def make_request(**overrides):
	values = {
		"city": "Алматы",
		"date": REQUEST_DATE,
		"event_type": "корпоратив",
		"category": "Ведущий",
		"budget_kzt": 200_000,
		"duration_hours": 4.0,
		"language": "русский",
	}
	values.update(overrides)
	return RecommendationRequest(**values)


def test_category_not_found():
	response = recommend([make_vendor()], make_request(category="Флорист"))

	assert response.status == "category_not_found"
	assert response.results == []


def test_no_eligible_candidates_includes_rejection_counts():
	vendor = make_vendor(
		busy_dates={REQUEST_DATE},
		event_formats=["свадьба"],
		price_from_kzt=300_000,
		max_hours=2.0,
	)

	response = recommend([vendor], make_request(duration_hours=4.0))

	assert response.status == "no_eligible_candidates"
	assert response.results == []
	assert response.debug["pool_size"] == 1
	assert response.debug["eligible_count"] == 0
	assert response.debug["rejection_counts"] == {
		"busy_on_date": 1,
		"duration_exceeded": 1,
		"over_budget": 1,
		"unsupported_event_format": 1,
	}
	assert "1 заняты на дату" in response.message


def test_matched_returns_at_most_three_sorted_cards():
	vendors = [make_vendor(f"vendor-{index}", price_from_kzt=price)
		for index, price in enumerate([300_000, 100_000, 200_000, 50_000])]

	response = recommend(vendors, make_request())

	assert response.status == "matched"
	assert [card.id for card in response.results] == [
		"vendor-3", "vendor-1", "vendor-2"
	]
	assert len(response.results) == 3


def test_busy_vendor_is_never_returned():
	vendors = [
		make_vendor("busy", busy_dates={REQUEST_DATE}),
		make_vendor("free"),
	]

	response = recommend(vendors, make_request())

	assert [card.id for card in response.results] == ["free"]


def test_over_budget_vendor_is_never_returned():
	response = recommend(
		[make_vendor("expensive", price_from_kzt=300_000)],
		make_request(),
	)

	assert response.status == "no_eligible_candidates"
	assert response.results == []


def test_unsupported_format_vendor_is_never_returned():
	response = recommend(
		[make_vendor("wrong-format", event_formats=["свадьба"])],
		make_request(),
	)

	assert response.status == "no_eligible_candidates"
	assert response.results == []


def test_same_request_has_deterministic_order():
	vendors = [
		make_vendor("b", price_from_kzt=100_000),
		make_vendor("a", price_from_kzt=100_000),
	]

	first = recommend(vendors, make_request())
	second = recommend(vendors, make_request())

	assert [card.id for card in first.results] == ["a", "b"]
	assert [card.id for card in first.results] == [card.id for card in second.results]


def test_returns_all_matches_when_fewer_than_three_exist():
	response = recommend(
		[make_vendor("one"), make_vendor("two")],
		make_request(),
	)

	assert len(response.results) == 2