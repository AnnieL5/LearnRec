"""
profile_parser.py
-----------------
Turns a natural-language learner profile into structured preferences.

Example input:
    "I know basic Python and want fast hands-on AI projects."

Extracted structure:
    - experience_level: beginner
    - learning_style: hands-on, fast-paced
    - goals: ["AI projects"]
    - interests: ["python", "ai"]
    - time_constraint: short

The parser uses simple keyword rules (no extra AI model) so it is easy to
read and extend. Semantic matching still happens later in recommender.py.
"""

import re
from typing import Literal

from pydantic import BaseModel, Field

ExperienceLevel = Literal["beginner", "intermediate", "advanced", "unknown"]
TimeConstraint = Literal["short", "medium", "long", "unknown"]
LearningStyle = Literal[
    "hands-on",
    "project-based",
    "video",
    "reading",
    "fast-paced",
    "unknown",
]


class LearnerProfile(BaseModel):
    """
    Structured preferences extracted from the user's free-text profile.

    These fields drive both resource fetching (search_query) and ranking.
    """

    raw_text: str = Field(..., description="Original user message")
    experience_level: ExperienceLevel = "unknown"
    learning_styles: list[LearningStyle] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    time_constraint: TimeConstraint = "unknown"
    search_query: str = Field(
        ...,
        description="Short topic string sent to YouTube/article fetchers",
    )
    embedding_text: str = Field(
        ...,
        description="Rich text built from preferences for semantic embeddings",
    )


# --- Keyword dictionaries (add more phrases anytime) ---

BEGINNER_PHRASES = (
    "new to",
    "just starting",
    "never learned",
    "no experience",
    "beginner",
    "basics",
    "basic ",
    "intro to",
    "introduction to",
    "for beginners",
    "first time",
)

INTERMEDIATE_PHRASES = (
    "some experience",
    "already know the basics",
    "comfortable with",
    "intermediate",
    "beyond basics",
)

ADVANCED_PHRASES = (
    "already know",
    "experienced",
    "advanced",
    "expert",
    "deep dive",
    "graduate level",
)

STYLE_KEYWORDS: dict[LearningStyle, tuple[str, ...]] = {
    "hands-on": ("hands-on", "hands on", "practical", "build", "coding exercises"),
    "project-based": ("project", "projects", "portfolio", "build something"),
    "video": ("video", "watch", "lecture", "youtube"),
    "reading": ("read", "article", "documentation", "docs", "textbook", "book"),
    "fast-paced": ("fast", "quick", "short", "crash course", "in a hurry", "no time"),
}

TIME_KEYWORDS: dict[TimeConstraint, tuple[str, ...]] = {
    "short": ("fast", "quick", "short", "brief", "crash course", "weekend", "hour"),
    "medium": ("few weeks", "month", "steady pace"),
    "long": ("deep", "comprehensive", "full course", "semester", "thorough"),
}

# Common learning topics we recognize in profiles (extend as needed)
KNOWN_TOPICS = (
    "python",
    "javascript",
    "java",
    "c++",
    "web development",
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "ai",
    "data science",
    "calculus",
    "linear algebra",
    "statistics",
    "algorithms",
    "recursion",
    "git",
    "react",
    "html",
    "css",
    "pytorch",
    "tensorflow",
    "neural networks",
    "computer science",
)


def parse_profile(text: str) -> LearnerProfile:
    """
    Main entry point: free text → LearnerProfile.

    Steps:
        1. Detect experience level from phrases
        2. Detect learning styles and time constraints
        3. Pull out topic interests and goals
        4. Build search_query (for APIs) and embedding_text (for ranking)
    """
    cleaned = " ".join(text.strip().split())
    lowered = cleaned.lower()

    experience = _detect_experience(lowered)
    styles = _detect_learning_styles(lowered)
    time_constraint = _detect_time_constraint(lowered)
    interests = _extract_topics(lowered)
    goals = _extract_goals(cleaned, interests)

    search_query = _build_search_query(interests, goals, cleaned)
    embedding_text = _build_embedding_text(
        raw=cleaned,
        experience=experience,
        styles=styles,
        goals=goals,
        interests=interests,
        time_constraint=time_constraint,
    )

    return LearnerProfile(
        raw_text=cleaned,
        experience_level=experience,
        learning_styles=styles,
        goals=goals,
        interests=interests,
        time_constraint=time_constraint,
        search_query=search_query,
        embedding_text=embedding_text,
    )


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    """Return True if any phrase appears in text."""
    return any(phrase in text for phrase in phrases)


def _detect_experience(text: str) -> ExperienceLevel:
    """Guess how advanced the learner is from common phrases."""
    if _contains_any(text, ADVANCED_PHRASES):
        return "advanced"
    if _contains_any(text, INTERMEDIATE_PHRASES):
        return "intermediate"
    if _contains_any(text, BEGINNER_PHRASES):
        return "beginner"
    return "unknown"


def _detect_learning_styles(text: str) -> list[LearningStyle]:
    """Collect every learning style that matches keywords in the profile."""
    matched: list[LearningStyle] = []
    for style, keywords in STYLE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            matched.append(style)
    return matched


def _detect_time_constraint(text: str) -> TimeConstraint:
    """Estimate how much time the learner wants to spend."""
    for constraint, keywords in TIME_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return constraint
    return "unknown"


def _extract_topics(text: str) -> list[str]:
    """
    Find known subject areas mentioned in the profile.

    We scan for KNOWN_TOPICS so fetchers get useful search terms
    (e.g. "machine learning" instead of the whole sentence).
    """
    found: list[str] = []
    for topic in KNOWN_TOPICS:
        if topic in text and topic not in found:
            found.append(topic)
    return found


def _extract_goals(text: str, interests: list[str]) -> list[str]:
    """
    Pull short goal phrases from patterns like "want to ..." or "learn ...".

    Falls back to interests if no clear goal phrase is found.
    """
    goals: list[str] = []

    patterns = [
        r"want to (.+?)(?:\.|$)",
        r"want (.+?)(?:\.|$)",
        r"learn (.+?)(?:\.|$)",
        r"looking for (.+?)(?:\.|$)",
        r"goal is to (.+?)(?:\.|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            goal = match.group(1).strip(" .")
            if len(goal) > 3:
                goals.append(goal)

    if not goals and interests:
        goals = [f"learn {interests[0]}"]

    return goals[:3]


def _build_search_query(interests: list[str], goals: list[str], raw: str) -> str:
    """
    Compact string for YouTube / Dev.to / course keyword filters.

    Prefer explicit topics; otherwise use the first few words of the profile.
    """
    if interests:
        return " ".join(interests[:4])
    if goals:
        return goals[0][:120]
    return raw[:120]


def _build_embedding_text(
    raw: str,
    experience: ExperienceLevel,
    styles: list[LearningStyle],
    goals: list[str],
    interests: list[str],
    time_constraint: TimeConstraint,
) -> str:
    """
    Combine structured preferences into one paragraph for embeddings.

    Why not embed only the raw sentence?
        Adding labeled fields (Goals, Experience, Style) helps the model
        align resources even when the user's wording differs from a video title.

    This string is what sentence-transformers encodes in recommender.py.
    """
    style_text = ", ".join(styles) if styles else "flexible"
    goal_text = "; ".join(goals) if goals else raw
    interest_text = ", ".join(interests) if interests else "general learning"

    parts = [
        f"Learner profile: {raw}",
        f"Learning goals: {goal_text}",
        f"Experience level: {experience}",
        f"Preferred learning style: {style_text}",
        f"Topics of interest: {interest_text}",
        f"Time available: {time_constraint}",
    ]
    return ". ".join(parts)
