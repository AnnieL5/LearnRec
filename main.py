"""
main.py
-------
FastAPI app for the multi-source AI Study Resource Recommender.

Supports natural-language learner profiles instead of bare keyword queries.

Run locally:
    uvicorn main:app --reload

Interactive docs: http://127.0.0.1:8000/docs
"""

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from aggregator import fetch_all_resources
from profile_parser import LearnerProfile, parse_profile
from recommender import rank_resources
from schemas import RankedLearningResource

load_dotenv()

app = FastAPI(
    title="Study Resource Recommender",
    description=(
        "Recommends videos, courses, articles, and documentation "
        "from natural-language learner profiles using semantic search "
        "and multi-factor scoring."
    ),
    version="3.0.0",
)


class RecommendRequest(BaseModel):
    """
    JSON body for POST /recommend.

    Send a sentence describing goals, experience, style, and interests.
    """

    profile: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        examples=[
            "I know basic Python and want fast hands-on AI projects.",
            "I already know calculus and want fast machine learning tutorials.",
        ],
        description="Natural-language learner profile",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="How many recommendations to return",
    )


class RecommendResponse(BaseModel):
    """JSON response with parsed profile and ranked resources."""

    profile: LearnerProfile
    total_candidates: int
    sources_fetched: dict[str, int]
    recommendations: list[RankedLearningResource]


@app.get("/")
def root() -> dict[str, str]:
    """Health check."""
    return {
        "message": "Study Resource Recommender with learner profiles is running.",
        "try": "POST /recommend with a natural-language profile",
    }


@app.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest) -> RecommendResponse:
    """
    Recommend learning resources for a natural-language learner profile.

    Pipeline:
        1. profile_parser  — extract goals, level, style, interests, time
        2. aggregator      — fetch resources using profile.search_query
        3. recommender     — semantic + difficulty + style + topic scoring
        4. return top_k ranked resources with score breakdown
    """
    learner_profile = parse_profile(request.profile.strip())

    resources, source_counts = fetch_all_resources(learner_profile.search_query)

    if not resources:
        raise HTTPException(
            status_code=404,
            detail=(
                "No resources found. Check your internet connection "
                "or try rephrasing your profile with clearer topics."
            ),
        )

    ranked = rank_resources(learner_profile, resources, top_k=request.top_k)

    return RecommendResponse(
        profile=learner_profile,
        total_candidates=len(resources),
        sources_fetched=source_counts,
        recommendations=ranked,
    )
