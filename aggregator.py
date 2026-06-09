"""
aggregator.py
-------------
Merges resources from every fetcher into one list before ranking.

Architecture
============

    User query
        │
        ▼
    ┌───────────────────────────────────────────────────┐
    │  aggregator.fetch_all_resources(query)            │
    │                                                   │
    │   youtube_fetcher  ──> videos                     │
    │   course_fetcher   ──> courses      ──> MERGE     │
    │   article_fetcher  ──> articles + docs            │
    └───────────────────────────────────────────────────┘
        │
        ▼
    recommender.rank_resources(merged list)
        │
        ▼
    Top 5 RankedLearningResource objects

Each fetcher is independent:
    - Returns the same LearningResource schema
    - Can fail without breaking the others (YouTube needs an API key; others don't)
"""

from schemas import LearningResource
from article_fetcher import fetch_articles
from course_fetcher import fetch_courses
from youtube_fetcher import fetch_videos


def fetch_all_resources(query: str) -> tuple[list[LearningResource], dict[str, int]]:
    """
    Call every fetcher, merge results, and report counts per source.

    Args:
        query: The student's learning topic.

    Returns:
        (merged_resources, source_counts)
        source_counts maps fetcher name → number of items fetched (for debugging/UI).
    """
    merged: list[LearningResource] = []
    counts: dict[str, int] = {}

    # --- Fetcher 1: YouTube videos (optional API key) ---
    try:
        videos = fetch_videos(query)
        merged.extend(videos)
        counts["youtube"] = len(videos)
    except Exception:
        counts["youtube"] = 0

    # --- Fetcher 2: Curated + filtered courses ---
    try:
        courses = fetch_courses(query)
        merged.extend(courses)
        counts["courses"] = len(courses)
    except Exception:
        counts["courses"] = 0

    # --- Fetcher 3: Articles (Dev.to) + docs (Wikipedia + curated) ---
    try:
        articles = fetch_articles(query)
        merged.extend(articles)
        counts["articles"] = len(articles)
    except Exception:
        counts["articles"] = 0

    return merged, counts
