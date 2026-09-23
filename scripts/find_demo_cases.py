"""Find reproducible demo requests from the anonymized dataset."""

import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.dataset import load_vendors
from app.recommender import recommend
from app.schemas import RecommendationRequest


DATASET = ROOT / "data" / "hackathon_dataset_anonymized.csv"
DEMO_FILE = ROOT / "demo" / "demo_cases.json"
DENSE_CATEGORIES = ("Ведущий", "Фотограф", "Банкетный зал")
RARE_CATEGORIES = (
	"Флорист",
	"Декоратор",
	"Подарки и сувениры",
	"Ведущий церемонии",
	"Фото и видеобудки",
	"Отель",
	"Инструменталист",
)


def _dataset_path() -> Path:
	if DATASET.exists():
		return DATASET
	csv_files = sorted((ROOT / "data").glob("*.csv"))
	if not csv_files:
		raise FileNotFoundError("No CSV dataset found in data/")
	return csv_files[0]


def _request(
	city: str,
	category: str,
	event_type: str,
	budget_kzt: int,
	request_date: date,
	duration_hours: float | None = None,
	language: str | None = None,
) -> RecommendationRequest:
	return RecommendationRequest(
		city=city,
		date=request_date,
		event_type=event_type,
		category=category,
		budget_kzt=budget_kzt,
		duration_hours=duration_hours,
		language=language,
	)


def _request_dict(request: RecommendationRequest) -> dict:
	return {
		"city": request.city,
		"date": request.date.isoformat(),
		"event_type": request.event_type,
		"category": request.category,
		"budget_kzt": request.budget_kzt,
		"duration_hours": request.duration_hours,
		"language": request.language,
	}


def _result_ids(response) -> list[str]:
	return [card.id for card in response.results]


def _case(name, request, response, reason) -> dict:
	return {
		"scenario_name": name,
		"request": _request_dict(request),
		"expected_status": response.status,
		"short_reason_why_this_demo_is_useful": reason,
		"expected_result_ids": _result_ids(response),
	}


def _pool(vendors, city, category):
	return [
		vendor for vendor in vendors
		if vendor.city == city and category in vendor.categories
	]


def _best_format(pool):
	return Counter(
		fmt for vendor in pool for fmt in vendor.event_formats
	).most_common(1)[0][0]


def _free_date(vendors) -> date:
	all_busy_dates = {
		busy_date for vendor in vendors for busy_date in vendor.busy_dates
	}
	return max(all_busy_dates, default=date(2026, 9, 23)) + timedelta(days=1)


def _matched_candidate(vendors, categories, minimum_pool=1):
	free_date = _free_date(vendors)
	for category in categories:
		for city in sorted({vendor.city for vendor in vendors}):
			pool = _pool(vendors, city, category)
			if len(pool) < minimum_pool:
				continue
			event_type = _best_format(pool)
			budget = max(vendor.price_from_kzt for vendor in pool)
			request = _request(city, category, event_type, budget, free_date)
			response = recommend(vendors, request)
			if response.status == "matched":
				return request, response
	return None


def _find_no_result(vendors):
	free_date = _free_date(vendors)
	for category in RARE_CATEGORIES + DENSE_CATEGORIES:
		for city in sorted({vendor.city for vendor in vendors}):
			pool = _pool(vendors, city, category)
			if not pool:
				continue
			event_type = _best_format(pool)
			budget = min(vendor.price_from_kzt for vendor in pool) - 1
			request = _request(city, category, event_type, budget, free_date)
			response = recommend(vendors, request)
			if response.status == "no_eligible_candidates":
				return request, response
		raise RuntimeError("Could not find a no-result scenario")


def _find_date_comparison(vendors):
	free_date = _free_date(vendors)
	for category in DENSE_CATEGORIES + RARE_CATEGORIES:
		for city in sorted({vendor.city for vendor in vendors}):
			pool = _pool(vendors, city, category)
			if not pool:
				continue
			event_type = _best_format(pool)
			budget = max(vendor.price_from_kzt for vendor in pool)
			base = _request(city, category, event_type, budget, free_date)
			base_response = recommend(vendors, base)
			if base_response.status != "matched":
				continue
			busy_dates = sorted({
				busy_date for vendor in pool for busy_date in vendor.busy_dates
			})
			for busy_date in busy_dates:
				comparison = _request(city, category, event_type, budget, busy_date)
				comparison_response = recommend(vendors, comparison)
				if (
					comparison_response.status == "matched"
					and _result_ids(base_response) != _result_ids(comparison_response)
				):
					return base, base_response, comparison, comparison_response
		raise RuntimeError("Could not find a date-comparison scenario")


def build_demo_cases(vendors) -> list[dict]:
	dense = _matched_candidate(vendors, DENSE_CATEGORIES, minimum_pool=3)
	rare = _matched_candidate(vendors, RARE_CATEGORIES)
	no_result_request, no_result_response = _find_no_result(vendors)
	date_a, response_a, date_b, response_b = _find_date_comparison(vendors)
	if dense is None or rare is None:
		raise RuntimeError("Could not find dense or rare matched scenario")

	dense_request, dense_response = dense
	rare_request, rare_response = rare
	return [
		_case(
			"dense_category",
			dense_request,
			dense_response,
			"Большая категория показывает отбор и ranking top-кандидатов.",
		),
		_case(
			"rare_category",
			rare_request,
			rare_response,
			"Редкая категория показывает реальный pool и число доступных результатов.",
		),
		_case(
			"no_result",
			no_result_request,
			no_result_response,
			"Бюджет ниже минимальной цены pool, поэтому message показывает причину отказа.",
		),
		{
			"scenario_name": "date_comparison",
			"request": {
				"request_a": _request_dict(date_a),
				"request_b": _request_dict(date_b),
			},
			"expected_status": {
				"request_a": response_a.status,
				"request_b": response_b.status,
			},
			"short_reason_why_this_demo_is_useful": (
				"Одинаковые условия на разные даты показывают влияние busy_dates."
			),
			"expected_result_ids": {
				"request_a": _result_ids(response_a),
				"request_b": _result_ids(response_b),
			},
		},
	]


def main() -> None:
	vendors = load_vendors(_dataset_path())
	cases = build_demo_cases(vendors)
	DEMO_FILE.parent.mkdir(parents=True, exist_ok=True)
	DEMO_FILE.write_text(
		json.dumps(cases, ensure_ascii=False, indent=2) + "\n",
		encoding="utf-8",
	)
	print(f"Saved {len(cases)} demo cases to {DEMO_FILE.relative_to(ROOT)}")
	for case in cases:
		print(f"- {case['scenario_name']}: {case['expected_status']}")


if __name__ == "__main__":
	main()
