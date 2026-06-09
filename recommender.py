"""
recommender.py
--------------
Turns a user query + video list into ranked recommendations using embeddings.

How it works (high level):
1. Convert text into numeric vectors (embeddings) with sentence-transformers.
2. Compare the query vector to each video vector with cosine similarity.
3. Higher similarity = better match → return the top 5 videos.
"""

from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Model name on Hugging Face — small, fast, good for beginners
MODEL_NAME = "all-MiniLM-L6-v2"

# Load once when the module is imported (avoids reloading on every request)
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Lazy-load the embedding model so startup stays fast."""
    global _model
    if _model is None:
        # SentenceTransformer downloads the model on first use (~80 MB)
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _video_to_text(video: dict[str, Any]) -> str:
    """
    Combine title and description into one string for embedding.

    The model sees one piece of text per video; joining fields
    gives it more context than the title alone.
    """
    title = video.get("title", "")
    description = video.get("description", "")
    return f"{title}. {description}".strip()


def rank_videos(
    query: str,
    videos: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Rank videos by semantic similarity to the user's learning query.

    Args:
        query: Student's question or topic (e.g. "how do for loops work in Python").
        videos: List from youtube_fetcher.fetch_videos().
        top_k: How many recommendations to return (default 5).

    Returns:
        Same video dicts, sorted best-first, each with an extra "similarity_score"
        field (0 to 1, higher = more relevant).
    """
    if not videos:
        return []

    model = get_model()

    # --- Step 1: Build text lists ---
    # One string for the query, one per video
    query_text = query.strip()
    video_texts = [_video_to_text(v) for v in videos]

    # --- Step 2: Embeddings ---
    # encode() turns each sentence into a vector (e.g. length 384 for MiniLM)
    # normalize_embeddings=True makes cosine similarity = dot product of vectors
    query_embedding = model.encode([query_text], normalize_embeddings=True)
    video_embeddings = model.encode(video_texts, normalize_embeddings=True)

    # --- Step 3: Cosine similarity ---
    # cosine_similarity compares one query vector to all video vectors at once
    # Result shape: (1, num_videos) — one score per video
    scores = cosine_similarity(query_embedding, video_embeddings)[0]

    # --- Step 4: Sort by score (highest first) ---
    # argsort gives indices that would sort ascending; [::-1] reverses to descending
    ranked_indices = np.argsort(scores)[::-1]

    recommendations: list[dict[str, Any]] = []
    for index in ranked_indices[:top_k]:
        video = dict(videos[index])  # copy so we don't mutate the original
        video["similarity_score"] = round(float(scores[index]), 4)
        recommendations.append(video)

    return recommendations
