"""Hard filtering of vendors for a recommendation request."""

from .schemas import Evaluation, RecommendationRequest, Vendor


def vendor_in_city_and_category(
	vendor: Vendor,
	request: RecommendationRequest,
) -> bool:
	"""Return whether a vendor belongs to the request's initial pool."""
	return vendor.city == request.city and request.category in vendor.categories


def evaluate_vendor(vendor: Vendor, request: RecommendationRequest) -> Evaluation:
	"""Evaluate hard-filter conditions and collect every rejection reason."""
	available = request.date not in vendor.busy_dates
	format_match = request.event_type in vendor.event_formats
	budget_match = vendor.price_from_kzt <= request.budget_kzt
	duration_match = (
		request.duration_hours is None
		or vendor.max_hours is None
		or vendor.max_hours >= request.duration_hours
	)
	language_match = (
		request.language is None or request.language in vendor.languages
	)

	rejection_reasons = []
	if not available:
		rejection_reasons.append("busy_on_date")
	if not format_match:
		rejection_reasons.append("unsupported_event_format")
	if not budget_match:
		rejection_reasons.append("over_budget")
	if not duration_match:
		rejection_reasons.append("duration_exceeded")

	return Evaluation(
		vendor=vendor,
		available=available,
		format_match=format_match,
		budget_match=budget_match,
		duration_match=duration_match,
		language_match=language_match,
		rejection_reasons=rejection_reasons,
	)


def passes_hard_filters(evaluation: Evaluation) -> bool:
	"""Return whether an evaluation passed all hard-filter conditions."""
	return not evaluation.rejection_reasons


def filter_city_category_pool(
	vendors: list[Vendor],
	request: RecommendationRequest,
) -> list[Vendor]:
	"""Keep vendors matching the request's city and category."""
	return [vendor for vendor in vendors if vendor_in_city_and_category(vendor, request)]


def evaluate_pool(
	vendors: list[Vendor],
	request: RecommendationRequest,
) -> list[Evaluation]:
	"""Evaluate each vendor in the supplied pool without filtering it."""
	return [evaluate_vendor(vendor, request) for vendor in vendors]
