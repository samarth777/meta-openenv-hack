"""YAML-declared task graders for OpenEnv validation."""

from __future__ import annotations

from dataclasses import dataclass

from peer_review_env.grading import grade_review
from peer_review_env.models import PeerReviewAction
from peer_review_env.tasks import TASK_ORDER, TASKS, TaskSpec

_SCORE_EPSILON = 1e-4


def _strict_unit_score(value: float) -> float:
    return min(1.0 - _SCORE_EPSILON, max(_SCORE_EPSILON, float(value)))


def _task_for_difficulty(difficulty: str) -> TaskSpec:
    for task_id in TASK_ORDER:
        task = TASKS[task_id]
        if task.difficulty == difficulty:
            return task
    # Fallback should never trigger with the shipped snapshot.
    return TASKS[TASK_ORDER[0]]


@dataclass
class _BaseDifficultyGrader:
    difficulty: str

    def grade(self, trajectory=None) -> float:
        # Use a deterministic baseline prediction so grader output is stable.
        del trajectory
        task = _task_for_difficulty(self.difficulty)
        score = grade_review(task, PeerReviewAction()).total_score
        return _strict_unit_score(score)


class EasyGrader(_BaseDifficultyGrader):
    def __init__(self):
        super().__init__(difficulty="easy")


class MediumGrader(_BaseDifficultyGrader):
    def __init__(self):
        super().__init__(difficulty="medium")


class HardGrader(_BaseDifficultyGrader):
    def __init__(self):
        super().__init__(difficulty="hard")
