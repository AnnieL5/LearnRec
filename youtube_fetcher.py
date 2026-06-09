"""
youtube_fetcher.py
------------------
Fetches educational YouTube *videos* and normalizes them to LearningResource.

Free API: YouTube Data API v3 (Search endpoint)
Docs: https://developers.google.com/youtube/v3/docs/search/list

Set in environment:
    YOUTUBE_API_KEY=your_key_here
"""

import os

import httpx

from schemas import LearningResource

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def fetch_videos(query: str, max_results: int = 12) -> list[LearningResource]:
    """
    Search YouTube for educational videos related to the query.

    Returns normalized LearningResource objects with resource_type="video".
    Returns an empty list if the API key is missing (other fetchers can still run).
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        # No key → skip YouTube instead of crashing the whole request
        return []

    search_query = f"{query} tutorial education"

    params = {
        "part": "snippet",
        "q": search_query,
        "type": "video",
        "maxResults": max_results,
        "videoCategoryId": "27",  # Education category
        "relevanceLanguage": "en",
        "key": api_key,
    }

    response = httpx.get(f"{YOUTUBE_API_BASE}/search", params=params, timeout=15.0)
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        message = data["error"].get("message", "Unknown YouTube API error")
        raise ValueError(f"YouTube API error: {message}")

    resources: list[LearningResource] = []

    for item in data.get("items", []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]
        title = snippet.get("title", "")
        description = (snippet.get("description") or "")[:500]

        # Guess difficulty from common words in title/description (simple heuristic)
        difficulty = _guess_difficulty(f"{title} {description}")

        resources.append(
            LearningResource(
                title=title,
                description=description,
                url=f"https://www.youtube.com/watch?v={video_id}",
                source="YouTube",
                difficulty=difficulty,
                tags=_extract_tags(query, title),
                resource_type="video",
            )
        )

    return resources


def _guess_difficulty(text: str) -> str:
    """Very simple keyword-based difficulty guess for beginners."""
    lowered = text.lower()
    if any(word in lowered for word in ("beginner", "intro", "101", "basics", "for kids")):
        return "beginner"
    if any(word in lowered for word in ("advanced", "expert", "deep dive", "masterclass")):
        return "advanced"
    if any(word in lowered for word in ("intermediate", "beyond basics")):
        return "intermediate"
    return "unknown"


def _extract_tags(query: str, title: str) -> list[str]:
    """Pull a few topic words from the query and title for metadata."""
    words = f"{query} {title}".lower().replace(",", " ").split()
    # Keep words longer than 3 chars, skip very common filler
    stopwords = {"the", "and", "for", "with", "how", "what", "this", "that", "from"}
    tags = [w.strip("?.!") for w in words if len(w) > 3 and w not in stopwords]
    # Unique tags, preserve order, cap at 5
    seen: set[str] = set()
    unique: list[str] = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique.append(tag)
        if len(unique) >= 5:
            break
    return unique
