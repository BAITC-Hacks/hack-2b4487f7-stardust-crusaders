from datetime import date

from app.explanations import (
	build_card_explanation,
	build_empty_result_message,
	build_evidence,
)
from app.recommender import recommend
from app.schemas import RecommendationRequest, Vendor


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
		"description": "Ведущий корпоративных мероприятий.",
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


def test_explanation_contains_price_or_budget():
	evidence = build_evidence(make_vendor(), make_request())
	explanation = build_card_explanation(evidence)

	assert "100000" in explanation or "200000" in explanation


def test_explanation_contains_language_or_duration_fact():
	evidence = build_evidence(make_vendor(), make_request(language="русский"))
	explanation = build_card_explanation(evidence)

	assert "русский" in explanation or "4.0" in explanation


def test_explanation_has_no_generic_forbidden_phrases():
	evidence = build_evidence(make_vendor(), make_request())
	explanation = build_card_explanation(evidence).lower()

	for phrase in (
		"отличный выбор",
		"идеально подходит",
		"хороший вариант",
		"рекомендуем",
		"подходит для вашего мероприятия",
	):
		assert phrase not in explanation


def test_no_eligible_message_is_nonempty_and_has_numeric_diagnostics():
	vendor = make_vendor(
		busy_dates={date(2026, 9, 23)},
		event_formats=["свадьба"],
		price_from_kzt=300_000,
		max_hours=2.0,
	)

	response = recommend([vendor], make_request())

	assert response.status == "no_eligible_candidates"
	assert response.message
	assert all(str(number) in response.message for number in (1, 1, 1, 1, 1))


def test_empty_result_message_builder_contains_pool_and_rejection_counts():
	message = build_empty_result_message(
		make_request(),
		3,
		{
			"busy_on_date": 1,
			"unsupported_event_format": 1,
			"over_budget": 1,
			"duration_exceeded": 1,
		},
	)

	assert "3 профилей" in message
	assert all(str(number) in message for number in (1, 1, 1, 1))


def test_demo_cases_file_contains_four_scenarios():
	import json
	from pathlib import Path

	cases = json.loads(
		(Path(__file__).parents[1] / "demo" / "demo_cases.json").read_text(
			encoding="utf-8"
		)
	)

	assert len(cases) >= 4
	assert {case["scenario_name"] for case in cases} >= {
		"dense_category",
		"rare_category",
		"no_result",
		"date_comparison",
	}