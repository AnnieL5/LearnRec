"""
youtube_fetcher.py
------------------
Fetches educational YouTube videos for a learning query.

Uses the official YouTube Data API v3 (Search endpoint).
You need a free API key: https://console.cloud.google.com/

Set it in your environment:
    YOUTUBE_API_KEY=your_key_here
"""

import os
from typing import Any

import httpx

# YouTube's public API base URL (no trailing slash)
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def fetch_videos(query: str, max_results: int = 15) -> list[dict[str, Any]]:
    """
    Search YouTube for videos related to a learning topic.

    Args:
        query: What the student wants to learn (e.g. "Python loops").
        max_results: How many videos to fetch before ranking (we rank down to 5 later).

    Returns:
        A list of dicts, each with:
            - video_id: YouTube ID (used to build the watch URL)
            - title: Video title
            - description: Short text about the video (used for embeddings)
            - url: Full link to watch on YouTube

    Raises:
        ValueError: If YOUTUBE_API_KEY is missing or the API returns an error.
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise ValueError(
            "Missing YOUTUBE_API_KEY. Create a key in Google Cloud Console "
            "and set it as an environment variable."
        )

    # Add "tutorial" to bias results toward educational content
    search_query = f"{query} tutorial education"

    params = {
        "part": "snippet",  # snippet = title, description, channel, etc.
        "q": search_query,
        "type": "video",
        "maxResults": max_results,
        "videoCategoryId": "27",  # 27 = Education category on YouTube
        "relevanceLanguage": "en",
        "key": api_key,
    }

    # httpx is an async-friendly HTTP client; .get() is synchronous and fine here
    response = httpx.get(f"{YOUTUBE_API_BASE}/search", params=params, timeout=15.0)
    response.raise_for_status()
    data = response.json()

    # YouTube wraps errors inside JSON even when HTTP status is 200 sometimes
    if "error" in data:
        message = data["error"].get("message", "Unknown YouTube API error")
        raise ValueError(f"YouTube API error: {message}")

    items = data.get("items", [])
    videos: list[dict[str, Any]] = []

    for item in items:
        # Each search result has id.videoId and snippet fields
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]

        videos.append(
            {
                "video_id": video_id,
                "title": snippet.get("title", ""),
                # Descriptions can be long; first 500 chars is enough for embeddings
                "description": (snippet.get("description") or "")[:500],
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
        )

    return videos
