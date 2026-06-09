"""
recommender.py
--------------
Semantic ranking for ANY LearningResource — videos, courses, articles, or docs.

Pipeline (same for all resource types):
    1. Turn query + each resource into text → embeddings (sentence-transformers)
    2. Cosine similarity scores how close each resource is to the query
    3. Return the top_k highest-scoring resources
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from schemas import LearningResource, RankedLearningResource

MODEL_NAME = "all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Lazy-load the embedding model (downloaded once, ~80 MB)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _resource_to_text(resource: LearningResource) -> str:
    """
    Build one string per resource for the embedding model.

    Including tags and difficulty helps the model match queries like
    "beginner Python tutorial" even when those words aren't in the title.
    """
    tags = ", ".join(resource.tags) if resource.tags else ""
    parts = [
        resource.title,
        resource.description,
        f"Type: {resource.resource_type}",
        f"Source: {resource.source}",
        f"Difficulty: {resource.difficulty}",
    ]
    if tags:
        parts.append(f"Tags: {tags}")
    return ". ".join(parts)


def rank_resources(
    query: str,
    resources: list[LearningResource],
    top_k: int = 5,
) -> list[RankedLearningResource]:
    """
    Rank a merged list of resources by semantic similarity to the query.

    Args:
        query: Student's learning question or topic.
        resources: Combined output from all fetchers (YouTube, courses, articles…).
        top_k: Number of recommendations to return (default 5).

    Returns:
        Top RankedLearningResource objects sorted best-first.
    """
    if not resources:
        return []

    model = get_model()
    query_text = query.strip()
    resource_texts = [_resource_to_text(r) for r in resources]

    # Embeddings: text → numeric vectors (384 dimensions for MiniLM)
    query_embedding = model.encode([query_text], normalize_embeddings=True)
    resource_embeddings = model.encode(resource_texts, normalize_embeddings=True)

    # Cosine similarity: 1.0 = identical meaning, 0.0 = unrelated
    scores = cosine_similarity(query_embedding, resource_embeddings)[0]

    ranked_indices = np.argsort(scores)[::-1]

    recommendations: list[RankedLearningResource] = []
    for index in ranked_indices[:top_k]:
        base = resources[index]
        recommendations.append(
            RankedLearningResource(
                **base.model_dump(),
                similarity_score=round(float(scores[index]), 4),
            )
        )

    return recommendations
