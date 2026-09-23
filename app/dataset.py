"""CSV loading and normalization for contractor profiles."""

import csv
from datetime import date
from pathlib import Path

from .schemas import Vendor


def parse_pipe_list(value: str) -> list[str]:
	"""Return trimmed, non-empty values from a pipe-separated field."""
	return [part.strip() for part in (value or "").split("|") if part.strip()]


def parse_bool(value) -> bool:
	"""Parse a boolean CSV value."""
	if isinstance(value, bool):
		return value
	normalized = str(value).strip().lower()
	if normalized == "true":
		return True
	if normalized == "false":
		return False
	raise ValueError(f"Expected True or False, got {value!r}")


def parse_optional_float(value: str) -> float | None:
	"""Parse a possibly empty floating-point CSV value."""
	normalized = (value or "").strip()
	return None if not normalized else float(normalized)


def parse_busy_dates(value: str) -> set[date]:
	"""Parse pipe-separated ISO dates into a set."""
	return {date.fromisoformat(item) for item in parse_pipe_list(value)}


def load_vendors(csv_path: str | Path) -> list[Vendor]:
	"""Load and normalize all vendor rows from a CSV file."""
	path = Path(csv_path)
	with path.open("r", encoding="utf-8-sig", newline="") as stream:
		reader = csv.DictReader(stream)
		if reader.fieldnames is None:
			raise ValueError("CSV must contain a header")

		required = {
			"id", "anon_name", "categories", "city", "city_imputed",
			"synthetic", "price_from_kzt", "price_imputed", "event_formats",
			"languages", "max_hours", "busy_dates", "description",
		}
		missing = required.difference(reader.fieldnames)
		if missing:
			raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")

		vendors = []
		for row in reader:
			if not any((value or "").strip() for value in row.values()):
				continue
			vendors.append(
				Vendor(
					id=(row["id"] or "").strip(),
					anon_name=(row["anon_name"] or "").strip(),
					categories=parse_pipe_list(row["categories"]),
					city=(row["city"] or "").strip(),
					city_imputed=parse_bool(row["city_imputed"]),
					synthetic=parse_bool(row["synthetic"]),
					price_from_kzt=int((row["price_from_kzt"] or "").strip()),
					price_imputed=parse_bool(row["price_imputed"]),
					event_formats=parse_pipe_list(row["event_formats"]),
					languages=parse_pipe_list(row["languages"]),
					max_hours=parse_optional_float(row["max_hours"]),
					busy_dates=parse_busy_dates(row["busy_dates"]),
					description=(row["description"] or "").strip(),
				)
			)
	return vendors
