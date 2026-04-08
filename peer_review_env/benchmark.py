"""Local tuple-based benchmark wrapper used by inference and tests."""

from __future__ import annotations

from .models import PeerReviewAction, PeerReviewObservation, PeerReviewState
from .server.peer_review_env_environment import PeerReviewEnvironment


BENCHMARK_NAME = "peer_review_env"


class PeerReviewBenchmark:
    """Local benchmark wrapper with Gym-style `step` output."""

    def __init__(self):
        self._env = PeerReviewEnvironment()

    def reset(self, **kwargs) -> PeerReviewObservation:
        return self._env.reset(**kwargs)

    def step(
        self, action: PeerReviewAction
    ) -> tuple[PeerReviewObservation, float, bool, dict[str, object]]:
        observation = self._env.step(action)
        reward = float(observation.reward or 0.0)
        done = bool(observation.done)
        info = {
            "score_breakdown": observation.score_breakdown,
            "last_action_error": observation.last_action_error,
        }
        return observation, reward, done, info

    def state(self) -> PeerReviewState:
        return self._env.state

    def close(self) -> None:
        self._env.close()
