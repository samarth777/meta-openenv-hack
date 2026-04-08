# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Environment logic for the OpenReview score-prediction benchmark."""

from __future__ import annotations

import hashlib
from typing import Optional
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment

try:
    from ..grading import grade_review
    from ..models import PeerReviewAction, PeerReviewObservation, PeerReviewState
    from ..tasks import TASK_ORDER, TASKS, TaskSpec
except ImportError:
    from grading import grade_review
    from models import PeerReviewAction, PeerReviewObservation, PeerReviewState
    from tasks import TASK_ORDER, TASKS, TaskSpec


class PeerReviewEnvironment(
    Environment[PeerReviewAction, PeerReviewObservation, PeerReviewState]
):
    """Score-prediction environment over a frozen OpenReview/NeurIPS snapshot."""

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        super().__init__()
        self._task: Optional[TaskSpec] = None
        self._state = PeerReviewState(episode_id=str(uuid4()), step_count=0)
        self._last_signature: Optional[str] = None

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs,
    ) -> PeerReviewObservation:
        task_id = kwargs.get("task_id")
        self._task = self._select_task(task_id=task_id, seed=seed)
        self._last_signature = None
        self._state = PeerReviewState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_id=self._task.task_id,
            task_name=self._task.task_name,
            difficulty=self._task.difficulty,
            max_steps=self._task.max_steps,
            done=False,
            best_score=0.0,
            last_score=0.0,
            last_action_error=None,
        )
        return self._build_observation(
            reward=0.0,
            done=False,
            current_score=0.0,
            best_score=0.0,
            score_breakdown={},
            feedback=[
                "Read the full paper markdown and predict the mean OpenReview rating and confidence.",
                "You can revise your numeric prediction for shaped reward before finalizing.",
            ],
        )

    def step(
        self,
        action: PeerReviewAction,
        timeout_s: Optional[float] = None,
        **kwargs,
    ) -> PeerReviewObservation:
        del timeout_s, kwargs

        if self._task is None:
            return self.reset()

        if self._state.done:
            self._state.last_action_error = "episode_already_completed"
            return self._build_observation(
                reward=-0.10,
                done=True,
                current_score=self._state.last_score,
                best_score=self._state.best_score,
                score_breakdown={},
                feedback=[
                    "Episode already completed. Reset before submitting a new prediction."
                ],
            )

        self._state.step_count += 1
        self._state.last_action_error = action.metadata.get("parse_error")

        grading = grade_review(self._task, action)
        current_score = grading.total_score
        best_before = self._state.best_score
        best_after = max(best_before, current_score)

        improvement_bonus = max(0.0, best_after - best_before)
        reward = current_score + (0.15 * improvement_bonus)
        feedback = list(grading.feedback)

        signature = self._signature(action)
        if signature == self._last_signature:
            reward -= 0.08
            feedback.append(
                "Repeated the previous numeric prediction without material changes."
            )
        self._last_signature = signature

        reward -= 0.01

        if action.finalize and current_score < 0.35:
            reward -= 0.05
            feedback.append("Finalized early with a weak prediction.")

        done = (
            action.finalize
            or self._state.step_count >= self._task.max_steps
            or current_score >= 0.97
        )
        if current_score >= 0.97 and not action.finalize:
            feedback.append(
                "Episode auto-completed because your prediction closely matches the ground-truth scores."
            )
        elif self._state.step_count >= self._task.max_steps and not action.finalize:
            feedback.append("Max prediction attempts reached.")

        reward = max(0.0, min(1.0, round(reward, 4)))
        self._state.done = done
        self._state.last_score = current_score
        self._state.best_score = best_after

        return self._build_observation(
            reward=reward,
            done=done,
            current_score=current_score,
            best_score=best_after,
            score_breakdown=grading.as_dict(),
            feedback=feedback,
        )

    @property
    def state(self) -> PeerReviewState:
        return self._state

    def _select_task(self, task_id: Optional[str], seed: Optional[int]) -> TaskSpec:
        if task_id:
            return TASKS[task_id]
        if seed is None:
            return TASKS[TASK_ORDER[0]]
        return TASKS[TASK_ORDER[seed % len(TASK_ORDER)]]

    def _build_observation(
        self,
        *,
        reward: float,
        done: bool,
        current_score: float,
        best_score: float,
        score_breakdown: dict[str, float],
        feedback: list[str],
    ) -> PeerReviewObservation:
        assert self._task is not None
        attempts_remaining = max(0, self._task.max_steps - self._state.step_count)
        return PeerReviewObservation(
            task_id=self._task.task_id,
            task_name=self._task.task_name,
            difficulty=self._task.difficulty,
            objective=self._task.objective,
            paper_markdown=self._task.paper_markdown,
            rating_scale="1-10 mean human reviewer rating.",
            confidence_scale="1-5 mean human reviewer confidence.",
            attempts_remaining=attempts_remaining,
            current_score=round(current_score, 4),
            best_score=round(best_score, 4),
            score_breakdown=score_breakdown,
            feedback=feedback,
            last_action_error=self._state.last_action_error,
            done=done,
            reward=reward,
            metadata={
                "forum_id": self._task.forum_id,
                "source_url": self._task.source_url,
                "review_count": self._task.review_count,
                "decision": self._task.decision,
                "step": self._state.step_count,
            },
        )

    def _signature(self, action: PeerReviewAction) -> str:
        payload = "|".join(
            [
                f"{action.rating:.2f}",
                f"{action.confidence:.2f}",
                str(action.finalize),
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
