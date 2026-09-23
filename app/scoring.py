"""Deterministic baseline scoring for hard-filtered vendors."""

import re

from .schemas import RecommendationRequest, Vendor


BUDGET_WEIGHT = 0.30
LANGUAGE_WEIGHT = 0.25
DURATION_WEIGHT = 0.20
DESCRIPTION_WEIGHT = 0.25


def _budget_fit(vendor: Vendor, request: RecommendationRequest) -> float:
	"""Prefer a reasonable spend near 80% of the available budget."""
	ratio = vendor.price_from_kzt / request.budget_kzt
	return max(0.0, 1.0 - abs(ratio - 0.8) / 0.8)


def _language_fit(vendor: Vendor, request: RecommendationRequest) -> float:
	if request.language is None:
		return 0.5
	return 1.0 if request.language in vendor.languages else 0.1


def _duration_fit(vendor: Vendor, request: RecommendationRequest) -> float:
	if request.duration_hours is None:
		return 0.5
	if vendor.max_hours is None:
		return 0.6
	return min(1.0, request.duration_hours / vendor.max_hours)


def _keywords(value: str) -> set[str]:
	return set(re.findall(r"[^\W_]+", value.lower(), flags=re.UNICODE))


def _description_fit(vendor: Vendor, request: RecommendationRequest) -> float:
	keywords = _keywords(request.event_type) | _keywords(request.category)
	if not keywords:
		return 0.5
	description_words = _keywords(vendor.description)
	return len(keywords & description_words) / len(keywords)


def score_vendor(vendor: Vendor, request: RecommendationRequest) -> dict[str, float]:
	"""Return deterministic component and total scores in the range [0, 1]."""
	budget = _budget_fit(vendor, request)
	language = _language_fit(vendor, request)
	duration = _duration_fit(vendor, request)
	description = _description_fit(vendor, request)
	total = (
		BUDGET_WEIGHT * budget
		+ LANGUAGE_WEIGHT * language
		+ DURATION_WEIGHT * duration
		+ DESCRIPTION_WEIGHT * description
	)
	return {
		"budget": budget,
		"language": language,
		"duration": duration,
		"description": description,
		"total": total,
	}


def score_candidate(vendor: Vendor, request: RecommendationRequest) -> dict[str, float]:
	"""Compatibility alias for callers that use candidate terminology."""
	return score_vendor(vendor, request)
