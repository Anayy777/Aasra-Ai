from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.recommender import recommend_from_transcript


app = FastAPI(
    title="Aasra-Ai Recommendation Service",
    version="1.0.0",
)


class RecommendRequest(BaseModel):
    transcript: str = Field(
        min_length=1
    )

    user_latitude: Optional[float] = None

    user_longitude: Optional[float] = None

    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
    )

    language_code: Optional[str] = None


@app.get("/")
def health_check():
    return {
        "service": "Aasra-Ai Recommendation Service",
        "status": "running",
    }


@app.post("/recommend")
def recommend(
    request: RecommendRequest,
):
    result = recommend_from_transcript(
        transcript=request.transcript,
        user_latitude=request.user_latitude,
        user_longitude=request.user_longitude,
        top_k=request.top_k,
        language_code=request.language_code,
    )

    return result