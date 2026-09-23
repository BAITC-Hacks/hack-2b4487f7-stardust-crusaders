from datetime import date
from pathlib import Path

from app.dataset import load_vendors


DATASET_PATH = Path(__file__).parents[1] / "data" / "hackathon_dataset_anonymized.csv"


def test_load_vendors_normalizes_dataset():
    vendors = load_vendors(DATASET_PATH)

    assert len(vendors) == 66
    assert vendors[0].id
    assert all(isinstance(category, str) for category in vendors[0].categories)
    assert isinstance(vendors[0].categories, list)
    assert isinstance(vendors[0].busy_dates, set)
    assert all(isinstance(item, date) for item in vendors[0].busy_dates)


def test_load_vendors_parses_empty_max_hours_and_boolean_fields():
    vendors = load_vendors(DATASET_PATH)

    assert vendors[0].max_hours is None
    assert all(isinstance(vendor.synthetic, bool) for vendor in vendors)
    assert all(isinstance(vendor.city_imputed, bool) for vendor in vendors)
    assert all(isinstance(vendor.price_imputed, bool) for vendor in vendors)