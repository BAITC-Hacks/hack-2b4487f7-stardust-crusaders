"""Reproducible, read-only profile audit using only the Python standard library."""

import csv
from collections import Counter
from datetime import date
from pathlib import Path
from statistics import mean
import sys


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "hackathon_dataset_anonymized.csv"
LEGACY_DATASET = ROOT / "data" / "hackathon-dataset-anonymized.csv"
MULTIVALUE_FIELDS = ("categories", "event_formats", "languages", "busy_dates")
FLAG_FIELDS = ("synthetic", "city_imputed", "price_imputed")
REQUIRED_FIELDS = ("city", "max_hours", *MULTIVALUE_FIELDS, *FLAG_FIELDS)
MISSING_CITY = "(missing city)"


def split_values(value):
    """Trim pipe-separated values and count each distinct value once per profile."""
    return tuple(sorted({part.strip() for part in (value or "").split("|")
                         if part.strip()}))


def load_profiles(stream):
    """Read CSV without mutating it; blank scalar values become None."""
    reader = csv.DictReader(stream)
    if reader.fieldnames is None:
        raise ValueError("CSV is empty: no header or profiles.")
    reader.fieldnames = [name.strip() for name in reader.fieldnames]
    if len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("CSV contains duplicate column names.")
    missing = sorted(set(REQUIRED_FIELDS) - set(reader.fieldnames))
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    profiles = []
    for row in reader:
        if None in row:
            raise ValueError(f"CSV line {reader.line_num}: too many columns.")
        if not any((value or "").strip() for value in row.values()):
            continue
        profile = {key: (value or "").strip() or None for key, value in row.items()}
        for field in MULTIVALUE_FIELDS:
            profile[field] = split_values(profile[field])
        for field in FLAG_FIELDS:
            value = profile[field]
            if value is not None and value.lower() not in ("true", "false"):
                raise ValueError(f"CSV line {reader.line_num}: invalid {field}={value!r}.")
            profile[field] = None if value is None else value.lower() == "true"
        dates = []
        for value in profile["busy_dates"]:
            try:
                parsed = date.fromisoformat(value)
                if parsed.isoformat() != value:
                    raise ValueError("Expected YYYY-MM-DD")
            except ValueError as exc:
                raise ValueError(
                    f"CSV line {reader.line_num}: invalid busy_dates date {value!r}; "
                    "expected YYYY-MM-DD."
                ) from exc
            dates.append(parsed)
        profile["busy_dates"] = tuple(dates)
        # max_hours is not used in this audit; preserve its text or None.
        profiles.append(profile)
    return profiles


def print_table(headers, rows):
    rows = [tuple(map(str, row)) for row in rows]
    widths = [max(len(header), max((len(row[i]) for row in rows), default=0))
              for i, header in enumerate(headers)]
    print(" | ".join(header.ljust(width) for header, width in zip(headers, widths)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(width) for value, width in zip(row, widths)))
    if not rows:
        print("(none)")


def print_audit(profiles):
    total = len(profiles)
    cities = Counter(profile["city"] or MISSING_CITY for profile in profiles)
    categories = Counter(category for profile in profiles for category in profile["categories"])
    cross = Counter((category, profile["city"] or MISSING_CITY)
                    for profile in profiles for category in profile["categories"])
    print(f"Total profiles: {total}")
    for title, values in (
        ("Cities", {profile["city"] for profile in profiles if profile["city"]}),
        ("Categories", categories),
        ("Event formats", {v for p in profiles for v in p["event_formats"]}),
        ("Languages", {v for p in profiles for v in p["languages"]}),
    ):
        print(f"{title}: {', '.join(sorted(values)) or '(none)'}")
    print("\nFlags:")
    for field in FLAG_FIELDS:
        print(f"  {field}=true: {sum(p[field] is True for p in profiles)}")
        print(f"  {field} missing: {sum(p[field] is None for p in profiles)}")
    print("\nMissing values:")
    for field in ("city", "max_hours", *MULTIVALUE_FIELDS):
        print(f"  {field}: {sum(not p[field] for p in profiles)}")

    print("\nProfiles by city:")
    print_table(("City", "Profiles"), sorted(cities.items()))
    print("\nProfiles by category:")
    print_table(("Category", "Profiles"), sorted(categories.items()))
    print("\nCategory x city (profiles):")
    city_names = sorted(cities)
    print_table(("Category", *city_names),
                [(category, *(cross[category, city] for city in city_names))
                 for category in sorted(categories)])
    ranked = sorted(categories.items(), key=lambda item: (-item[1], item[0]))
    print("\nTop dense categories (top 10 by profile count):")
    print_table(("Category", "Profiles"), ranked[:10])
    print("\nRare categories (<= 3 profiles):")
    print_table(("Category", "Profiles"),
                sorted((item for item in categories.items() if item[1] <= 3),
                       key=lambda item: (item[1], item[0])))

    busy_counts = [len(p["busy_dates"]) for p in profiles]
    december_counts = [sum(day.month == 12 for day in p["busy_dates"]) for p in profiles]
    print("\nBusy dates (distinct days per profile):")
    print(f"  Mean: {mean(busy_counts):.2f}" if total else "  Mean: n/a")
    print(f"  Min: {min(busy_counts)}" if total else "  Min: n/a")
    print(f"  Max: {max(busy_counts)}" if total else "  Max: n/a")
    print(f"  December mean: {mean(december_counts):.2f}" if total
          else "  December mean: n/a")
    print("\nCounting rules: one profile per nonblank CSV row; pipe values are trimmed")
    print("and deduplicated per profile. Category totals may exceed profile totals.")
    print("Empty busy_dates count as zero; means include all profiles.")
    print("December includes all years. Missing flags are not counted as true.")


def main():
    path = DATASET
    if not path.exists() and LEGACY_DATASET.exists():
        path = LEGACY_DATASET
        print(f"Note: {DATASET.name} not found; using {path.name}.", file=sys.stderr)
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            profiles = load_profiles(stream)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print(f"Audit failed for {path}: {exc}", file=sys.stderr)
        return 1
    print(f"Dataset: {path.relative_to(ROOT).as_posix()}")
    print_audit(profiles)
    return 0


if __name__ == "__main__":
    sys.exit(main())
