"""FastAPI entrypoint for ToiMatch AI recommendations."""

from datetime import date
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from .dataset import load_vendors
from .recommender import recommend
from .schemas import RecommendationRequest


VENDORS = load_vendors()

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
