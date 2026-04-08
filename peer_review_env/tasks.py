"""Task definitions for score prediction over full paper markdown."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


_SNAPSHOT_PATH = Path(__file__).with_name("data_snapshot.json")


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    task_name: str
    difficulty: Literal["easy", "medium", "hard"]
    objective: str
    forum_id: str
    source_url: str
    paper_markdown: str
    gold_rating_mean: float
    gold_confidence_mean: float
    review_count: int
    decision: str
    max_steps: int = 3


with _SNAPSHOT_PATH.open("r", encoding="utf-8") as handle:
    SNAPSHOT = json.load(handle)


def _difficulty_for_index(index: int, total: int) -> Literal["easy", "medium", "hard"]:
    if total <= 3:
        return ("easy", "medium", "hard")[min(index, 2)]
    ratio = index / max(1, total - 1)
    if ratio < 0.34:
        return "easy"
    if ratio < 0.67:
        return "medium"
    return "hard"


def _objective_for_snapshot(snapshot: dict[str, object]) -> str:
    difficulty = str(snapshot.get("difficulty") or "medium")
    if difficulty == "easy":
        return "Read the full paper markdown and predict the mean OpenReview rating and confidence."
    if difficulty == "hard":
        return "Read the full paper markdown and predict the mean OpenReview rating and confidence for this harder paper."
    return "Read the full paper markdown and predict the mean OpenReview rating and confidence for this paper."


def _build_task(task_id: str, meta: dict[str, str]) -> TaskSpec:
    snapshot = SNAPSHOT[task_id]
    forum = snapshot["forum"]
    decisions = forum.get("decisions") or []
    decision = decisions[0].get("decision") if decisions else "Unknown"
    return TaskSpec(
        task_id=task_id,
        task_name=str(snapshot["task_name"]),
        difficulty=meta["difficulty"],
        objective=meta["objective"],
        forum_id=str(forum["forum_id"]),
        source_url=str(snapshot["source_url"]),
        paper_markdown=str(forum["paper_markdown"]),
        gold_rating_mean=float(forum["rating_mean"]),
        gold_confidence_mean=float(forum["confidence_mean"]),
        review_count=int(forum["review_count"]),
        decision=str(decision),
    )


_snapshot_items = sorted(
    SNAPSHOT.items(),
    key=lambda item: (
        str(item[1].get("difficulty") or ""),
        item[0],
    ),
)

TASKS = {}
for index, (task_id, snapshot) in enumerate(_snapshot_items):
    difficulty = snapshot.get("difficulty") or _difficulty_for_index(
        index, len(_snapshot_items)
    )
    TASKS[task_id] = _build_task(
        task_id,
        {
            "difficulty": str(difficulty),
            "objective": _objective_for_snapshot(snapshot),
        },
    )

TASK_ORDER = tuple(TASKS.keys())
