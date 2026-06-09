"""
article_fetcher.py
------------------
Fetches *articles* and *documentation* from free APIs + static curated lists.

Sources used:
    1. Dev.to API  — programming articles (no API key required)
       https://developers.forem.com/api
    2. Wikipedia REST API — encyclopedia summaries (great for concepts)
       https://www.mediawiki.org/wiki/API:REST_API
    3. Curated documentation links — official docs that rarely change
"""

import httpx

from urllib.parse import quote

from schemas import LearningResource

DEVTO_API = "https://dev.to/api"
WIKIPEDIA_API = "https://en.wikipedia.org/w/rest.php/v1/search/page"
WIKIPEDIA_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary"

# ---------------------------------------------------------------------------
# Curated official documentation (resource_type="documentation")
# ---------------------------------------------------------------------------
CURATED_DOCUMENTATION: list[dict] = [
    {
        "title": "Python Official Documentation",
        "description": "The authoritative reference for Python syntax, standard library, and tutorials.",
        "url": "https://docs.python.org/3/tutorial/",
        "source": "Python Software Foundation",
        "difficulty": "beginner",
        "tags": ["python", "documentation", "tutorial"],
    },
    {
        "title": "MDN Web Docs: JavaScript Guide",
        "description": "Mozilla's complete guide to JavaScript for web development.",
        "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
        "source": "MDN",
        "difficulty": "beginner",
        "tags": ["javascript", "web", "documentation"],
    },
    {
        "title": "MDN Web Docs: HTML",
        "description": "Reference and learning materials for HTML elements and semantics.",
        "url": "https://developer.mozilla.org/en-US/docs/Web/HTML",
        "source": "MDN",
        "difficulty": "beginner",
        "tags": ["html", "web", "documentation"],
    },
    {
        "title": "W3Schools Python Tutorial",
        "description": "Beginner-friendly Python examples and quick reference pages.",
        "url": "https://www.w3schools.com/python/",
        "source": "W3Schools",
        "difficulty": "beginner",
        "tags": ["python", "tutorial", "beginner"],
    },
    {
        "title": "NumPy User Guide",
        "description": "Official NumPy documentation for arrays, linear algebra, and scientific Python.",
        "url": "https://numpy.org/doc/stable/user/",
        "source": "NumPy",
        "difficulty": "intermediate",
        "tags": ["python", "numpy", "data-science"],
    },
    {
        "title": "PyTorch Tutorials",
        "description": "Official step-by-step tutorials for building neural networks with PyTorch.",
        "url": "https://pytorch.org/tutorials/",
        "source": "PyTorch",
        "difficulty": "intermediate",
        "tags": ["pytorch", "deep-learning", "python", "ai"],
    },
    {
        "title": "Git Documentation",
        "description": "Official Git reference: commits, branches, merging, and workflows.",
        "url": "https://git-scm.com/doc",
        "source": "Git SCM",
        "difficulty": "beginner",
        "tags": ["git", "version-control", "documentation"],
    },
]


def fetch_articles(query: str, max_results: int = 8) -> list[LearningResource]:
    """
    Fetch articles and documentation, merge them, return normalized resources.

    Calls multiple sub-fetchers; failures in one source won't block the others.
    """
    resources: list[LearningResource] = []

    # --- Live API: Dev.to articles ---
    try:
        resources.extend(_fetch_from_devto(query, max_per_source=5))
    except Exception:
        pass  # Dev.to down? Still return docs + Wikipedia

    # --- Live API: Wikipedia summaries ---
    try:
        resources.extend(_fetch_from_wikipedia(query, max_per_source=4))
    except Exception:
        pass

    # --- Static curated documentation ---
    resources.extend(_fetch_curated_documentation(query, max_results=6))

    return resources[:max_results]


def _fetch_from_devto(query: str, max_per_source: int = 5) -> list[LearningResource]:
    """
    Dev.to free API: search recent articles by tag derived from the query.

    We pick the first meaningful word as a tag (e.g. "python" from "learn python loops").
    """
    tag = _pick_devto_tag(query)
    response = httpx.get(
        f"{DEVTO_API}/articles",
        params={"tag": tag, "per_page": max_per_source},
        timeout=12.0,
    )
    response.raise_for_status()

    articles: list[LearningResource] = []
    for item in response.json():
        title = item.get("title", "")
        description = item.get("description") or title
        url = item.get("url", "")

        raw_tags = item.get("tag_list") or []
        if isinstance(raw_tags, str):
            extra_tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        else:
            extra_tags = list(raw_tags)[:3]

        articles.append(
            LearningResource(
                title=title,
                description=description[:500],
                url=url if url.startswith("http") else f"https://dev.to{url}",
                source="Dev.to",
                difficulty="unknown",
                tags=[tag] + extra_tags[:3],
                resource_type="article",
            )
        )

    return articles


def _fetch_from_wikipedia(query: str, max_per_source: int = 4) -> list[LearningResource]:
    """
    Wikipedia REST search → fetch short summaries for top pages.

    Good for conceptual topics (e.g. "recursion", "machine learning").
    """
    response = httpx.get(
        WIKIPEDIA_API,
        params={"q": query, "limit": max_per_source},
        timeout=12.0,
        headers={"User-Agent": "StudyResourceRecommender/1.0 (education project)"},
    )
    response.raise_for_status()

    pages = response.json().get("pages", [])
    resources: list[LearningResource] = []

    for page in pages:
        title = page.get("title", "")
        key = page.get("key", "")
        if not key:
            continue

        # Get a short plain-text excerpt for the description
        summary_resp = httpx.get(
            f"{WIKIPEDIA_SUMMARY}/{quote(key, safe='')}",
            timeout=10.0,
            headers={"User-Agent": "StudyResourceRecommender/1.0 (education project)"},
        )
        if summary_resp.status_code != 200:
            continue

        summary_data = summary_resp.json()
        description = summary_data.get("extract", "")[:500]
        url = summary_data.get("content_urls", {}).get("desktop", {}).get("page", "")

        if not url:
            continue

        resources.append(
            LearningResource(
                title=f"Wikipedia: {title}",
                description=description,
                url=url,
                source="Wikipedia",
                difficulty="unknown",
                tags=["reference", "encyclopedia"],
                resource_type="documentation",
            )
        )

    return resources


def _fetch_curated_documentation(query: str, max_results: int = 6) -> list[LearningResource]:
    """Filter static documentation links by keyword overlap with the query."""
    query_words = [w.lower() for w in query.split() if len(w) > 2]

    scored: list[tuple[int, dict]] = []
    for doc in CURATED_DOCUMENTATION:
        searchable = f"{doc['title']} {doc['description']} {' '.join(doc['tags'])}".lower()
        score = sum(1 for word in query_words if word in searchable)
        scored.append((score, doc))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    if scored[0][0] == 0:
        picked = [doc for _, doc in scored[:max_results]]
    else:
        picked = [doc for score, doc in scored if score > 0][:max_results]

    return [
        LearningResource(
            title=d["title"],
            description=d["description"],
            url=d["url"],
            source=d["source"],
            difficulty=d["difficulty"],
            tags=d["tags"],
            resource_type="documentation",
        )
        for d in picked
    ]


def _pick_devto_tag(query: str) -> str:
    """
    Dev.to searches by tag, not free text. Map common topics to tags.

    Falls back to 'programming' if no known tag is found.
    """
    known_tags = [
        "python",
        "javascript",
        "java",
        "webdev",
        "machinelearning",
        "ai",
        "beginners",
        "tutorial",
        "react",
        "css",
        "html",
        "git",
        "algorithms",
        "datascience",
    ]
    lowered = query.lower()
    for tag in known_tags:
        if tag in lowered.replace(" ", "").replace("-", ""):
            return tag
        # Also match "machine learning" → machinelearning
        if tag == "machinelearning" and "machine learning" in lowered:
            return tag
    return "programming"
