"""Deterministic numeric grading for mean score prediction."""

from __future__ import annotations

from dataclasses import dataclass

from .models import PeerReviewAction
from .tasks import TaskSpec

# Task scores must be strictly within (0, 1) for submission validation.
_SCORE_EPSILON = 1e-4


def _clamp_open_unit_interval(value: float) -> float:
    return min(1.0 - _SCORE_EPSILON, max(_SCORE_EPSILON, value))


def _numeric_score(value: float, target: float, tolerance: float) -> float:
    raw = max(0.0, 1.0 - (abs(value - target) / tolerance))
    return round(_clamp_open_unit_interval(raw), 4)


@dataclass(frozen=True)
class GradingBreakdown:
    rating_error: float
    confidence_error: float
    rating_score: float
    confidence_score: float
    total_score: float
    feedback: list[str]

    def as_dict(self) -> dict[str, float]:
        return {
            "rating_error": self.rating_error,
            "confidence_error": self.confidence_error,
            "rating": self.rating_score,
            "confidence": self.confidence_score,
            "overall": self.total_score,
        }


def grade_review(task: TaskSpec, action: PeerReviewAction) -> GradingBreakdown:
    rating_error = round(abs(action.rating - task.gold_rating_mean), 4)
    confidence_error = round(abs(action.confidence - task.gold_confidence_mean), 4)
    rating_score = _numeric_score(action.rating, task.gold_rating_mean, 3.0)
    confidence_score = _numeric_score(action.confidence, task.gold_confidence_mean, 1.5)
    total_raw = (0.7 * rating_score) + (0.3 * confidence_score)
    total_score = round(_clamp_open_unit_interval(total_raw), 4)

    feedback: list[str] = []
    if rating_score < 0.95:
        feedback.append(
            f"Predicted rating is not yet close to the ground-truth mean ({task.gold_rating_mean:.2f})."
        )
    if confidence_score < 0.95:
        feedback.append(
            f"Predicted confidence is not yet close to the ground-truth mean ({task.gold_confidence_mean:.2f})."
        )
    if not feedback:
        feedback.append(
            "Prediction is very close to the OpenReview ground-truth scores."
        )

    return GradingBreakdown(
        rating_error=rating_error,
        confidence_error=confidence_error,
        rating_score=rating_score,
        confidence_score=confidence_score,
        total_score=total_score,
        feedback=feedback,
    )
