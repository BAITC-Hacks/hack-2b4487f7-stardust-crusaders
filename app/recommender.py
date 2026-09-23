"""Orchestration for deterministic contractor recommendations."""

from collections import Counter

from .filters import evaluate_pool, filter_city_category_pool, passes_hard_filters
from .scoring import score_vendor
from .schemas import (
	RecommendationCard,
	RecommendationRequest,
	RecommendationResponse,
	Vendor,
)


def _request_summary(request: RecommendationRequest) -> dict:
	return {
		"city": request.city,
		"date": request.date.isoformat(),
		"event_type": request.event_type,
		"category": request.category,
		"budget_kzt": request.budget_kzt,
		"duration_hours": request.duration_hours,
		"language": request.language,
	}


def _card(vendor: Vendor, request: RecommendationRequest) -> RecommendationCard:
	explanation = (
		f"Цена от {vendor.price_from_kzt} ₸ укладывается в бюджет "
		f"{request.budget_kzt} ₸. Формат «{request.event_type}» поддерживается, "
		f"подрядчик свободен на дату {request.date.isoformat()}."
	)
	return RecommendationCard(
		id=vendor.id,
		anon_name=vendor.anon_name,
		category=request.category,
		city=vendor.city,
		price_from_kzt=vendor.price_from_kzt,
		synthetic=vendor.synthetic,
		city_imputed=vendor.city_imputed,
		price_imputed=vendor.price_imputed,
		explanation=explanation,
	)


def recommend(
	vendors: list[Vendor],
	request: RecommendationRequest,
) -> RecommendationResponse:
	"""Build a deterministic recommendation response for one request."""
	request_summary = _request_summary(request)
	pool = filter_city_category_pool(vendors, request)
	if not pool:
		return RecommendationResponse(
			status="category_not_found",
			message=(
				f"В городе {request.city} нет подрядчиков категории "
				f"«{request.category}»."
			),
			results=[],
			debug={
				"pool_size": 0,
				"eligible_count": 0,
				"rejection_counts": {},
				"request_summary": request_summary,
			},
		)

	evaluations = evaluate_pool(pool, request)
	rejection_counts = Counter(
		reason
		for evaluation in evaluations
		for reason in evaluation.rejection_reasons
	)
	eligible = [
		evaluation.vendor
		for evaluation in evaluations
		if passes_hard_filters(evaluation)
	]
	debug = {
		"pool_size": len(pool),
		"eligible_count": len(eligible),
		"rejection_counts": dict(sorted(rejection_counts.items())),
		"request_summary": request_summary,
	}

	if not eligible:
		message = (
			f"В городе {request.city} найдено {len(pool)} профилей категории "
			f"«{request.category}», но подходящих подрядчиков нет: "
			f"{rejection_counts['busy_on_date']} заняты на дату, "
			f"{rejection_counts['unsupported_event_format']} не поддерживают формат, "
			f"{rejection_counts['over_budget']} выше бюджета, "
			f"{rejection_counts['duration_exceeded']} не подходят по длительности."
		)
		return RecommendationResponse(
			status="no_eligible_candidates",
			message=message,
			results=[],
			debug=debug,
		)

	scores = {vendor.id: score_vendor(vendor, request) for vendor in eligible}
	eligible.sort(
		key=lambda vendor: (
			-scores[vendor.id]["total"],
			vendor.price_from_kzt,
			vendor.id,
		)
	)
	debug["top_candidates"] = [
		{"id": vendor.id, "score_breakdown": scores[vendor.id]}
		for vendor in eligible[:3]
	]
	return RecommendationResponse(
		status="matched",
		message=f"Найдено подходящих подрядчиков: {len(eligible)}.",
		results=[_card(vendor, request) for vendor in eligible[:3]],
		debug=debug,
	)
