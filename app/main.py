"""FastAPI entrypoint for ToiMatch AI recommendations."""

from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from .dataset import load_vendors
from .recommender import recommend
from .schemas import RecommendationRequest


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _dataset_path() -> Path:
	preferred = DATA_DIR / "hackathon_dataset_anonymized.csv"
	if preferred.exists():
		return preferred
	csv_files = sorted(DATA_DIR.glob("*.csv"))
	if not csv_files:
		raise FileNotFoundError(f"No CSV dataset found in {DATA_DIR}")
	return csv_files[0]


VENDORS = load_vendors(_dataset_path())

app = FastAPI(title="ToiMatch AI")


class RecommendPayload(BaseModel):
	city: str
	date: date
	event_type: str
	category: str
	budget_kzt: int
	duration_hours: float | None = None
	language: str | None = None


@app.get("/health")
def health() -> dict[str, int | str]:
	return {"status": "ok", "vendors_loaded": len(VENDORS)}


@app.post("/recommend")
def recommend_endpoint(payload: RecommendPayload) -> dict:
	request = RecommendationRequest(
		city=payload.city,
		date=payload.date,
		event_type=payload.event_type,
		category=payload.category,
		budget_kzt=payload.budget_kzt,
		duration_hours=payload.duration_hours,
		language=payload.language,
	)
	return jsonable_encoder(recommend(VENDORS, request))
