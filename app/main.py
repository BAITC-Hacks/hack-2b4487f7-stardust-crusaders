"""FastAPI entrypoint for ToiMatch AI recommendations."""

from datetime import date
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, field_validator

from .dataset import load_vendors
from .recommender import recommend
from .schemas import RecommendationRequest, RecommendationResponse


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

	@field_validator("date")
	@classmethod
	def date_cannot_be_in_the_past(cls, value: date) -> date:
		if value < date.today():
			raise ValueError("Дата мероприятия не может быть в прошлом")
		return value


@app.get("/")
def root() -> dict[str, str]:
	return {
		"service": "ToiMatch AI",
		"health": "/health",
		"docs": "/docs",
	}


@app.get("/health")
def health() -> dict[str, int | str]:
	return {"status": "ok", "vendors_loaded": len(VENDORS)}


@app.post("/recommend", response_model=RecommendationResponse)
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
