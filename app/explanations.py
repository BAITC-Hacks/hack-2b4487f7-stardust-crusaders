"""Evidence-based explanations for recommendation cards."""

import re

from .schemas import RecommendationRequest, Vendor


def _tokens(value: str) -> set[str]:
	return set(re.findall(r"[^\W_]+", value.lower(), flags=re.UNICODE))


def _description_matches(vendor: Vendor, request: RecommendationRequest) -> tuple[list[str], list[str]]:
	keywords = sorted(_tokens(request.event_type) | _tokens(request.category))
	description_tokens = _tokens(vendor.description)
	found = [keyword for keyword in keywords if keyword in description_tokens]

	snippets = []
	for sentence in re.split(r"(?<=[.!?])\s+", vendor.description):
		if _tokens(sentence) & set(found):
			snippets.append(sentence.strip())
	return found, snippets[:2]


def build_evidence(
	vendor: Vendor,
	request: RecommendationRequest,
	score_breakdown: dict[str, float] | None = None,
) -> dict:
	"""Collect only source-backed facts used to explain one recommendation."""
	description_keywords, description_snippets = _description_matches(vendor, request)
	language_matched = (
		None
		if request.language is None
		else request.language in vendor.languages
	)
	evidence = {
		"price_from_kzt": vendor.price_from_kzt,
		"budget_kzt": request.budget_kzt,
		"budget_headroom": request.budget_kzt - vendor.price_from_kzt,
		"event_type": request.event_type,
		"event_format_matched": request.event_type in vendor.event_formats,
		"category": request.category,
		"languages": list(vendor.languages),
		"requested_language": request.language,
		"language_matched": language_matched,
		"duration_hours": request.duration_hours,
		"max_hours": vendor.max_hours,
		"description_keywords": description_keywords,
		"description_snippets": description_snippets,
		"synthetic": vendor.synthetic,
		"city_imputed": vendor.city_imputed,
		"price_imputed": vendor.price_imputed,
		"score_breakdown": dict(score_breakdown or {}),
	}
	return evidence


def build_card_explanation(evidence: dict) -> str:
	"""Render a short Russian explanation from evidence facts only."""
	price = evidence["price_from_kzt"]
	budget = evidence["budget_kzt"]
	headroom = evidence["budget_headroom"]
	first_sentence = (
		f"Цена {price} ₸ при бюджете {budget} ₸ (запас {headroom} ₸)."
	)

	format_status = "поддерживается" if evidence["event_format_matched"] else "не указан"
	second_facts = f"Формат «{evidence['event_type']}» {format_status}."
	if evidence["requested_language"] is not None:
		language_status = "найден" if evidence["language_matched"] else "не найден"
		second_facts += (
			f" Язык «{evidence['requested_language']}» {language_status}."
		)
	elif evidence["duration_hours"] is not None:
		max_hours = evidence["max_hours"]
		max_label = "не ограничена" if max_hours is None else f"{max_hours} ч"
		second_facts += (
			f" Длительность: {evidence['duration_hours']} ч из {max_label}."
		)

	return f"{first_sentence} {second_facts}"


def build_empty_result_message(
	request: RecommendationRequest,
	pool_size: int,
	rejection_counts: dict[str, int],
) -> str:
	"""Explain why a city/category pool produced no eligible candidates."""
	return (
		f"В городе {request.city} найдено {pool_size} профилей категории "
		f"«{request.category}», но подходящих подрядчиков нет: "
		f"{rejection_counts.get('busy_on_date', 0)} заняты на дату, "
		f"{rejection_counts.get('unsupported_event_format', 0)} не поддерживают формат, "
		f"{rejection_counts.get('over_budget', 0)} выше бюджета, "
		f"{rejection_counts.get('duration_exceeded', 0)} не подходят по длительности."
	)
