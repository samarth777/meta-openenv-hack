"""Typed models for the OpenReview score-prediction benchmark."""

from typing import Dict, List, Literal, Optional

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field


class PeerReviewAction(Action):
    """A single score prediction submission."""

    rating: float = Field(
        default=5.0,
        ge=1.0,
        le=10.0,
        description="Predicted mean OpenReview rating on a 1-10 scale.",
    )
    confidence: float = Field(
        default=3.0,
        ge=1.0,
        le=5.0,
        description="Predicted mean OpenReview confidence on a 1-5 scale.",
    )
    finalize: bool = Field(
        default=False,
        description="Whether this is the final prediction submission for the episode.",
    )


class PeerReviewObservation(Observation):
    """Observation returned after each score prediction submission."""

    task_id: str = Field(default="", description="Stable task identifier.")
    task_name: str = Field(default="", description="Human-readable task name.")
    difficulty: Literal["easy", "medium", "hard"] = Field(
        default="easy",
        description="Task difficulty bucket.",
    )
    objective: str = Field(default="", description="Episode objective.")
    paper_markdown: str = Field(
        default="",
        description="Full paper markdown shown to the agent.",
    )
    rating_scale: str = Field(
        default="1-10 mean reviewer rating.",
        description="Reminder for the rating scale.",
    )
    confidence_scale: str = Field(
        default="1-5 mean reviewer confidence.",
        description="Reminder for the confidence scale.",
    )
    attempts_remaining: int = Field(default=0, ge=0)
    current_score: float = Field(default=0.0, ge=0.0, le=1.0)
    best_score: float = Field(default=0.0, ge=0.0, le=1.0)
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    feedback: List[str] = Field(default_factory=list)
    last_action_error: Optional[str] = Field(default=None)


class PeerReviewState(State):
    """Current environment state for a single benchmark episode."""

    task_id: Optional[str] = Field(default=None)
    task_name: str = Field(default="")
    difficulty: Literal["easy", "medium", "hard"] = Field(default="easy")
    max_steps: int = Field(default=3, ge=1)
    done: bool = Field(default=False)
    best_score: float = Field(default=0.0, ge=0.0, le=1.0)
    last_score: float = Field(default=0.0, ge=0.0, le=1.0)
    last_action_error: Optional[str] = Field(default=None)
