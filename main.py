"""
main.py
-------
FastAPI app for the multi-source AI Study Resource Recommender.

Run locally:
    uvicorn main:app --reload

Interactive docs: http://127.0.0.1:8000/docs

Optional env var (for YouTube videos):
    YOUTUBE_API_KEY=your_key_here

Articles and courses work without any API key.
"""

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from aggregator import fetch_all_resources
from recommender import rank_resources
from schemas import RankedLearningResource

load_dotenv()

app = FastAPI(
    title="Study Resource Recommender",
    description=(
        "Recommends videos, courses, articles, and documentation "
        "using semantic search across multiple sources."
    ),
    version="2.0.0",
)


class RecommendRequest(BaseModel):
    """JSON body for POST /recommend."""

    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        examples=["Explain recursion in Python for beginners"],
        description="What the student wants to learn",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="How many recommendations to return",
    )


class RecommendResponse(BaseModel):
    """JSON response with ranked resources from all sources."""

    query: str
    total_candidates: int = Field(
        ...,
        description="How many resources were merged before ranking",
    )
    sources_fetched: dict[str, int] = Field(
        ...,
        description="Count per fetcher (youtube, courses, articles)",
    )
    recommendations: list[RankedLearningResource]


@app.get("/")
def root() -> dict[str, str]:
    """Health check."""
    return {
        "message": "Multi-source Study Resource Recommender is running.",
        "try": "POST /recommend",
    }


@app.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest) -> RecommendResponse:
    """
    Recommend the best learning resources for a query.

    Pipeline:
        1. aggregator  — fetch + merge from YouTube, courses, articles/docs
        2. recommender — embed query + resources, rank by cosine similarity
        3. return top_k results (mixed types: video, course, article, documentation)
    """
    query = request.query.strip()

    resources, source_counts = fetch_all_resources(query)

    if not resources:
        raise HTTPException(
            status_code=404,
            detail=(
                "No resources found. Check your internet connection "
                "or try a different query."
            ),
        )

    ranked = rank_resources(query, resources, top_k=request.top_k)

    return RecommendResponse(
        query=query,
        total_candidates=len(resources),
        sources_fetched=source_counts,
        recommendations=ranked,
    )
