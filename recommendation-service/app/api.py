from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.recommender import recommend_from_transcript


app = FastAPI(
    title="Aasra-Ai Recommendation Service",
    version="1.0.0"
)


class RecommendRequest(BaseModel):
    transcript: str
    user_latitude: float
    user_longitude: float
    top_k: int = Field(default=3, ge=1, le=10)


@app.get("/")
def health_check():
    return {
        "service": "Aasra-Ai Recommendation Service",
        "status": "running"
    }


@app.post("/recommend")
def recommend(request: RecommendRequest):

    result = recommend_from_transcript(
        transcript=request.transcript,
        user_latitude=request.user_latitude,
        user_longitude=request.user_longitude,
        top_k=request.top_k
    )

    return result