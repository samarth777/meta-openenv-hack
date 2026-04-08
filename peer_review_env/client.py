# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Async client for the OpenReview score-prediction environment."""

from __future__ import annotations

from typing import Any

from openenv.core.client_types import StepResult
from openenv.core.env_client import EnvClient

from .models import PeerReviewAction, PeerReviewObservation, PeerReviewState


class PeerReviewEnv(
    EnvClient[PeerReviewAction, PeerReviewObservation, PeerReviewState]
):
    """Typed WebSocket client for the score-prediction benchmark."""

    def _step_payload(self, action: PeerReviewAction) -> dict[str, Any]:
        return action.model_dump()

    def _parse_result(
        self, payload: dict[str, Any]
    ) -> StepResult[PeerReviewObservation]:
        obs_data = payload.get("observation", {})
        observation = PeerReviewObservation(
            task_id=obs_data.get("task_id", ""),
            task_name=obs_data.get("task_name", ""),
            difficulty=obs_data.get("difficulty", "easy"),
            objective=obs_data.get("objective", ""),
            paper_markdown=obs_data.get("paper_markdown", ""),
            rating_scale=obs_data.get("rating_scale", ""),
            confidence_scale=obs_data.get("confidence_scale", ""),
            attempts_remaining=obs_data.get("attempts_remaining", 0),
            current_score=obs_data.get("current_score", 0.0),
            best_score=obs_data.get("best_score", 0.0),
            score_breakdown=obs_data.get("score_breakdown", {}),
            feedback=obs_data.get("feedback", []),
            last_action_error=obs_data.get("last_action_error"),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
        )
        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict[str, Any]) -> PeerReviewState:
        return PeerReviewState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            task_id=payload.get("task_id"),
            task_name=payload.get("task_name", ""),
            difficulty=payload.get("difficulty", "easy"),
            max_steps=payload.get("max_steps", 3),
            done=payload.get("done", False),
            best_score=payload.get("best_score", 0.0),
            last_score=payload.get("last_score", 0.0),
            last_action_error=payload.get("last_action_error"),
        )

    async def submit_review(
        self,
        *,
        rating: float,
        confidence: float,
        finalize: bool = False,
    ) -> StepResult[PeerReviewObservation]:
        return await self.step(
            PeerReviewAction(
                rating=rating,
                confidence=confidence,
                finalize=finalize,
            )
        )
