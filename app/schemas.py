"""Data models used by the contractor recommender."""

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Vendor:
	id: str
	anon_name: str
	categories: list[str]
	city: str
	city_imputed: bool
	synthetic: bool
	price_from_kzt: int
	price_imputed: bool
	event_formats: list[str]
	languages: list[str]
	max_hours: float | None
	busy_dates: set[date]
	description: str


@dataclass(frozen=True)
class RecommendationRequest:
	city: str
	date: date
	event_type: str
	category: str
	budget_kzt: int
	duration_hours: float | None = None
	language: str | None = None


@dataclass
class Evaluation:
	vendor: Vendor
	available: bool
	format_match: bool
	budget_match: bool
	duration_match: bool
	language_match: bool
	rejection_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RecommendationCard:
	id: str
	anon_name: str
	category: str
	city: str
	price_from_kzt: int
	synthetic: bool
	city_imputed: bool
	price_imputed: bool
	explanation: str


@dataclass
class RecommendationResponse:
	status: str
	message: str
	results: list[RecommendationCard]
	debug: dict
