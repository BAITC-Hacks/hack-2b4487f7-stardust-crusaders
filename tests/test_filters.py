from datetime import date

from app.filters import (
	evaluate_vendor,
	filter_city_category_pool,
	passes_hard_filters,
)
from app.schemas import RecommendationRequest, Vendor


REQUEST_DATE = date(2026, 9, 23)


def make_vendor(**overrides):
	values = {
		"id": "vendor-1",
		"anon_name": "Test Vendor",
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
		"description": "Test description",
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


def test_pool_excludes_vendor_from_another_city():
	vendor = make_vendor(city="Астана")

	assert filter_city_category_pool([vendor], make_request()) == []


def test_pool_excludes_vendor_without_requested_category():
	vendor = make_vendor(categories=["Флорист"])

	assert filter_city_category_pool([vendor], make_request()) == []


def test_busy_vendor_gets_rejection_reason():
	evaluation = evaluate_vendor(
		make_vendor(busy_dates={REQUEST_DATE}), make_request()
	)

	assert "busy_on_date" in evaluation.rejection_reasons
	assert not passes_hard_filters(evaluation)


def test_over_budget_vendor_gets_rejection_reason():
	evaluation = evaluate_vendor(
		make_vendor(price_from_kzt=300_000), make_request()
	)

	assert "over_budget" in evaluation.rejection_reasons


def test_unsupported_format_gets_rejection_reason():
	evaluation = evaluate_vendor(
		make_vendor(event_formats=["свадьба"]), make_request()
	)

	assert "unsupported_event_format" in evaluation.rejection_reasons


def test_duration_exceeded_gets_rejection_reason():
	evaluation = evaluate_vendor(
		make_vendor(max_hours=2.0), make_request(duration_hours=3.0)
	)

	assert "duration_exceeded" in evaluation.rejection_reasons


def test_missing_max_hours_does_not_reject_duration():
	evaluation = evaluate_vendor(
		make_vendor(max_hours=None), make_request(duration_hours=100.0)
	)

	assert evaluation.duration_match is True
	assert passes_hard_filters(evaluation)


def test_language_mismatch_is_not_a_hard_rejection():
	evaluation = evaluate_vendor(
		make_vendor(languages=["английский"]), make_request(language="русский")
	)

	assert evaluation.language_match is False
	assert passes_hard_filters(evaluation)