"""
recommender.py
--------------
Multi-factor ranking for learning resources using a learner profile.

Scoring pipeline (each sub-score is 0.0 to 1.0):

    final_score =
        50% semantic similarity   (embeddings + cosine similarity)
      + 20% difficulty match      (resource level vs learner experience)
      + 15% learning-style match  (videos vs articles vs hands-on, etc.)
      + 15% topic relevance       (interest keywords vs resource tags/title)

What is semantic similarity?
----------------------------
1. Text is converted to a vector (embedding) — a list of numbers capturing meaning.
2. Cosine similarity measures the angle between two vectors:
      - 1.0  → very similar meaning
      - 0.0  → unrelated
3. Unlike keyword search, "ML tutorials" can match "machine learning course"
   because their embeddings are close in vector space.

We use all-MiniLM-L6-v2 (sentence-transformers) for embeddings.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from profile_parser import LearnerProfile
from schemas import LearningResource, RankedLearningResource, ScoreBreakdown

MODEL_NAME = "all-MiniLM-L6-v2"

# Weights must sum to 1.0 — adjust to tune recommendation behavior
WEIGHT_SEMANTIC = 0.50
WEIGHT_DIFFICULTY = 0.20
WEIGHT_STYLE = 0.15
WEIGHT_TOPIC = 0.15

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Lazy-load the embedding model (downloaded once, ~80 MB)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _resource_to_text(resource: LearningResource) -> str:
    """Build one string per resource for the embedding model."""
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


def _compute_semantic_scores(
    profile: LearnerProfile,
    resources: list[LearningResource],
) -> np.ndarray:
    """
    Embed the learner profile and each resource, then cosine-similarity.

    Returns one float score per resource (shape: num_resources).
    """
    model = get_model()
    query_embedding = model.encode([profile.embedding_text], normalize_embeddings=True)
    resource_texts = [_resource_to_text(r) for r in resources]
    resource_embeddings = model.encode(resource_texts, normalize_embeddings=True)

    # cosine_similarity returns a matrix; we take row 0 (one query vs many resources)
    return cosine_similarity(query_embedding, resource_embeddings)[0]


# Maps learner experience → how well each resource difficulty fits (0–1)
DIFFICULTY_FIT: dict[str, dict[str, float]] = {
    "beginner": {
        "beginner": 1.0,
        "intermediate": 0.55,
        "advanced": 0.2,
        "unknown": 0.5,
    },
    "intermediate": {
        "beginner": 0.45,
        "intermediate": 1.0,
        "advanced": 0.65,
        "unknown": 0.5,
    },
    "advanced": {
        "beginner": 0.15,
        "intermediate": 0.55,
        "advanced": 1.0,
        "unknown": 0.5,
    },
    "unknown": {
        "beginner": 0.6,
        "intermediate": 0.6,
        "advanced": 0.6,
        "unknown": 0.5,
    },
}


def _difficulty_score(profile: LearnerProfile, resource: LearningResource) -> float:
    """Score how appropriate the resource difficulty is for the learner."""
    table = DIFFICULTY_FIT.get(profile.experience_level, DIFFICULTY_FIT["unknown"])
    return table.get(resource.difficulty, 0.5)


def _learning_style_score(profile: LearnerProfile, resource: LearningResource) -> float:
    """
    Score how well the resource format matches preferred learning styles.

    If no style was detected, return a neutral 0.5 for every resource.
    """
    styles = profile.learning_styles
    if not styles:
        return 0.5

    text = f"{resource.title} {resource.description} {resource.resource_type}".lower()
    scores: list[float] = []

    for style in styles:
        if style == "hands-on":
            bonus = 0.85 if any(w in text for w in ("hands-on", "practice", "exercise", "lab")) else 0.45
            scores.append(bonus)
        elif style == "project-based":
            bonus = 0.9 if any(w in text for w in ("project", "build", "portfolio")) else 0.4
            scores.append(bonus)
        elif style == "video":
            bonus = 0.95 if resource.resource_type == "video" else 0.35
            scores.append(bonus)
        elif style == "reading":
            bonus = 0.9 if resource.resource_type in ("article", "documentation") else 0.35
            scores.append(bonus)
        elif style == "fast-paced":
            # Short articles/videos score higher than long multi-month courses
            if resource.resource_type in ("article", "documentation", "video"):
                scores.append(0.85)
            elif "crash" in text or "quick" in text or "intro" in text:
                scores.append(0.9)
            else:
                scores.append(0.4)
        else:
            scores.append(0.5)

    return float(sum(scores) / len(scores))


def _topic_score(profile: LearnerProfile, resource: LearningResource) -> float:
    """
    Keyword overlap between learner interests/goals and the resource.

    Complements semantic similarity with explicit topic matching.
    """
    if not profile.interests and not profile.goals:
        return 0.5

    resource_words = (
        f"{resource.title} {resource.description} {' '.join(resource.tags)}"
    ).lower()

    search_terms: list[str] = []
    search_terms.extend(profile.interests)
    for goal in profile.goals:
        search_terms.extend(goal.lower().split())

    # Remove tiny filler words
    stopwords = {"the", "and", "for", "with", "want", "learn", "basic", "to", "a"}
    terms = [t.strip(".,!?") for t in search_terms if len(t) > 2 and t not in stopwords]

    if not terms:
        return 0.5

    hits = sum(1 for term in terms if term in resource_words)
    # Normalize: 2+ hits → strong match
    return min(1.0, hits / 2.0)


def _final_score(
    semantic: float,
    difficulty: float,
    style: float,
    topic: float,
) -> float:
    """Weighted blend of all sub-scores."""
    return (
        WEIGHT_SEMANTIC * semantic
        + WEIGHT_DIFFICULTY * difficulty
        + WEIGHT_STYLE * style
        + WEIGHT_TOPIC * topic
    )


def rank_resources(
    profile: LearnerProfile,
    resources: list[LearningResource],
    top_k: int = 5,
) -> list[RankedLearningResource]:
    """
    Rank resources for a structured learner profile.

    Args:
        profile: Output of profile_parser.parse_profile().
        resources: Merged list from all fetchers.
        top_k: How many recommendations to return.

    Returns:
        Resources sorted by final_score (best first), with score breakdown.
    """
    if not resources:
        return []

    semantic_scores = _compute_semantic_scores(profile, resources)

    scored: list[tuple[float, int, ScoreBreakdown]] = []

    for index, resource in enumerate(resources):
        semantic = float(semantic_scores[index])
        difficulty = _difficulty_score(profile, resource)
        style = _learning_style_score(profile, resource)
        topic = _topic_score(profile, resource)

        breakdown = ScoreBreakdown(
            semantic=round(semantic, 4),
            difficulty=round(difficulty, 4),
            learning_style=round(style, 4),
            topic=round(topic, 4),
        )
        total = _final_score(semantic, difficulty, style, topic)
        scored.append((total, index, breakdown))

    # Sort by final_score descending
    scored.sort(key=lambda item: item[0], reverse=True)

    recommendations: list[RankedLearningResource] = []
    for total, index, breakdown in scored[:top_k]:
        base = resources[index]
        recommendations.append(
            RankedLearningResource(
                **base.model_dump(),
                similarity_score=breakdown.semantic,
                final_score=round(total, 4),
                score_breakdown=breakdown,
            )
        )

    return recommendations
