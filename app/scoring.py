"""Deterministic baseline scoring for hard-filtered vendors."""

import re

from .schemas import RecommendationRequest, Vendor


BUDGET_WEIGHT = 0.30
LANGUAGE_WEIGHT = 0.25
DURATION_WEIGHT = 0.20
DESCRIPTION_WEIGHT = 0.25
EVENT_KEYWORDS = {
	"свадьба", "той", "корпоратив", "конференция", "юбилей", "день рождения",
}
SEMANTIC_KEYWORDS = {
	"камерный", "премиум", "двуязычный", "интерактив", "фотозона", "банкет",
	"декор", "декоративный", "флористика", "welcome", "регистрация", "ведущий",
}


def _budget_fit(vendor: Vendor, request: RecommendationRequest) -> float:
	"""Prefer a reasonable spend near 80% of the available budget."""
	if request.budget_kzt <= 0:
		return 0.0
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


def _matches(tokens: set[str], keywords: set[str]) -> set[str]:
	return {
		keyword for keyword in keywords
		if keyword in tokens or any(
			token.startswith(keyword) for token in tokens if len(keyword) >= 4
		)
	}


def _description_fit(vendor: Vendor, request: RecommendationRequest) -> float:
	direct_keywords = _keywords(request.event_type) | _keywords(request.category)
	if not direct_keywords:
		return 0.5
	description_words = _keywords(vendor.description)
	direct_fit = len(_matches(description_words, direct_keywords)) / len(direct_keywords)
	semantic_keywords = EVENT_KEYWORDS | SEMANTIC_KEYWORDS
	semantic_fit = len(_matches(description_words, semantic_keywords)) / len(semantic_keywords)
	return 0.7 * direct_fit + 0.3 * semantic_fit


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
	breakdown = {
		"budget_fit": budget,
		"language_fit": language,
		"duration_fit": duration,
		"description_fit": description,
		"total": total,
	}
	# Keep the short names for compatibility with existing callers.
	breakdown.update({
		"budget": budget,
		"language": language,
		"duration": duration,
		"description": description,
	})
	return breakdown


def score_candidate(vendor: Vendor, request: RecommendationRequest) -> dict[str, float]:
	"""Compatibility alias for callers that use candidate terminology."""
	return score_vendor(vendor, request)
