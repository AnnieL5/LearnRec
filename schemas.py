"""
schemas.py
----------
Shared data shape for every learning resource, no matter where it came from.

Architecture idea:
    YouTube API ──┐
    Dev.to API  ──┼──> LearningResource (same fields) ──> merge ──> rank
    Static lists ─┘

Every fetcher converts its raw API response into this one format so the
recommender only needs to know about a single type of object.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Allowed values — keeps responses consistent for the frontend
ResourceType = Literal["video", "course", "article", "documentation"]
Difficulty = Literal["beginner", "intermediate", "advanced", "unknown"]


class LearningResource(BaseModel):
    """
    One study resource (video, course, article, or docs page).

    All fetchers must return objects that match these fields.
    """

    title: str = Field(..., description="Name of the resource")
    description: str = Field(..., description="Short summary used for AI ranking")
    url: str = Field(..., description="Link the student can open")
    source: str = Field(
        ...,
        description="Where it came from (e.g. YouTube, Dev.to, Curated)",
    )
    difficulty: Difficulty = Field(
        default="unknown",
        description="Estimated level: beginner, intermediate, advanced",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Topic keywords (e.g. python, algorithms)",
    )
    resource_type: ResourceType = Field(
        ...,
        description="Kind of resource: video, course, article, or documentation",
    )


class RankedLearningResource(LearningResource):
    """A resource after semantic ranking — includes the similarity score."""

    similarity_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Cosine similarity to the query (higher = better match)",
    )
