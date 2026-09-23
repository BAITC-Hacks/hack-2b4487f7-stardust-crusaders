"""Orchestration for deterministic contractor recommendations."""

from collections import Counter

from .explanations import (
	build_card_explanation,
	build_empty_result_message,
	build_evidence,
)
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


def _card(
	vendor: Vendor,
	request: RecommendationRequest,
	score_breakdown: dict[str, float],
) -> RecommendationCard:
	evidence = build_evidence(vendor, request, score_breakdown)
	return RecommendationCard(
		id=vendor.id,
		anon_name=vendor.anon_name,
		category=request.category,
		city=vendor.city,
		price_from_kzt=vendor.price_from_kzt,
		synthetic=vendor.synthetic,
		city_imputed=vendor.city_imputed,
		price_imputed=vendor.price_imputed,
		explanation=build_card_explanation(evidence),
		score=score_breakdown["total"],
		score_breakdown=score_breakdown,
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
				"ranked_candidate_ids": [],
				"score_breakdowns": {},
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
		"ranked_candidate_ids": [],
		"score_breakdowns": {},
	}

	if not eligible:
		return RecommendationResponse(
			status="no_eligible_candidates",
			message=build_empty_result_message(request, len(pool), rejection_counts),
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
	debug["ranked_candidate_ids"] = [vendor.id for vendor in eligible]
	debug["score_breakdowns"] = {
		vendor.id: scores[vendor.id] for vendor in eligible
	}
	debug["top_candidates"] = [
		{"id": vendor.id, "score_breakdown": scores[vendor.id]}
		for vendor in eligible[:3]
	]
	result_cards = [
		_card(vendor, request, scores[vendor.id])
		for vendor in eligible[:3]
	]
	message = f"Найдено подходящих подрядчиков: {len(eligible)}."
	if len(eligible) < 3:
		message = (
			f"Найдено {len(eligible)} подходящих подрядчиков из {len(pool)} профилей "
			"категории и города; трёх результатов нет. "
			f"Отсеяно: {rejection_counts['busy_on_date']} по занятости, "
			f"{rejection_counts['unsupported_event_format']} по формату, "
			f"{rejection_counts['over_budget']} по бюджету, "
			f"{rejection_counts['duration_exceeded']} по длительности."
		)
	return RecommendationResponse(
		status="matched",
		message=message,
		results=result_cards,
		debug=debug,
	)
