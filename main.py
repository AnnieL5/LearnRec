"""
main.py
-------
FastAPI app for the AI Study Resource Recommender.

Run locally:
    uvicorn main:app --reload

Then open: http://127.0.0.1:8000/docs  (interactive API docs)
"""

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from recommender import rank_videos
from youtube_fetcher import fetch_videos

# Load variables from a .env file if present (e.g. YOUTUBE_API_KEY)
load_dotenv()

app = FastAPI(
    title="Study Resource Recommender",
    description="Recommends educational YouTube videos using semantic search.",
    version="1.0.0",
)


# --- Request / response shapes (Pydantic validates JSON for us) ---


class RecommendRequest(BaseModel):
    """What the client sends in the POST body."""

    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        examples=["Explain recursion in Python for beginners"],
        description="What the student wants to learn",
    )


class VideoRecommendation(BaseModel):
    """One recommended video in the response."""

    video_id: str
    title: str
    description: str
    url: str
    similarity_score: float = Field(
        ...,
        description="0–1 score; higher means closer match to the query",
    )


class RecommendResponse(BaseModel):
    """Full API response."""

    query: str
    recommendations: list[VideoRecommendation]


# --- Routes ---


@app.get("/")
def root() -> dict[str, str]:
    """Simple health check — confirms the server is running."""
    return {"message": "Study Resource Recommender is running. Try POST /recommend"}


@app.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest) -> RecommendResponse:
    """
    Main endpoint: accept a learning query, return top 5 YouTube videos.

    Pipeline:
        1. Fetch candidate videos from YouTube
        2. Embed query + video text with sentence-transformers
        3. Rank by cosine similarity
        4. Return top 5
    """
    query = request.query.strip()

    try:
        videos = fetch_videos(query)
    except ValueError as exc:
        # Missing API key or YouTube returned an error message
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach YouTube API: {exc}",
        ) from exc

    if not videos:
        raise HTTPException(
            status_code=404,
            detail="No videos found for that query. Try different wording.",
        )

    ranked = rank_videos(query, videos, top_k=5)

    return RecommendResponse(
        query=query,
        recommendations=[VideoRecommendation(**video) for video in ranked],
    )
