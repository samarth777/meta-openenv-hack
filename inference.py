import json
import os
import re
from typing import Any

from openai import OpenAI

from peer_review_env import (
    BENCHMARK_NAME,
    PeerReviewAction,
    PeerReviewBenchmark,
    TASK_ORDER,
)


API_BASE_URL = os.getenv(
    "API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
)
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-3.1-flash-lite-preview")
HF_TOKEN = os.getenv("HF_TOKEN")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")


client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)


SYSTEM_PROMPT = """You are inside an RL benchmark that predicts OpenReview scores from full paper markdown.
Return valid JSON only with keys: rating, confidence, finalize.
rating must be between 1 and 10.
confidence must be between 1 and 5.
Use the paper markdown to estimate the mean human reviewer rating and confidence.
If the feedback says you are still off and attempts remain, revise. Otherwise finalize.
"""


def _extract_json_block(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _build_prompt(observation) -> str:
    feedback = "\n".join(f"- {item}" for item in observation.feedback) or "- None"
    return f"""
Task: {observation.task_name}
Difficulty: {observation.difficulty}
Objective: {observation.objective}
Attempts remaining: {observation.attempts_remaining}
Current score: {observation.current_score:.2f}
Best score: {observation.best_score:.2f}
Rating scale: {observation.rating_scale}
Confidence scale: {observation.confidence_scale}
Review count: {observation.metadata.get("review_count")}
Decision: {observation.metadata.get("decision")}

Paper markdown:
{observation.paper_markdown}

Grader feedback:
{feedback}
""".strip()


def _sanitize_action(
    payload: dict[str, Any], attempts_remaining: int
) -> PeerReviewAction:
    return PeerReviewAction(
        rating=float(payload.get("rating", 5.0)),
        confidence=float(payload.get("confidence", 3.0)),
        finalize=bool(payload.get("finalize", attempts_remaining <= 1)),
    )


def _single_line(text: str | None) -> str:
    if text is None:
        return "null"
    return re.sub(r"\s+", " ", str(text)).strip() or "null"


def run_task(task_id: str) -> list[float]:
    env = PeerReviewBenchmark()
    rewards: list[float] = []
    success = False
    steps = 0
    print(f"[START] task={task_id} env={BENCHMARK_NAME} model={MODEL_NAME}")
    try:
        observation = env.reset(task_id=task_id)
        done = False
        while not done:
            error = None
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": _build_prompt(observation)},
                    ],
                    temperature=0,
                )
                content = response.choices[0].message.content or "{}"
                action = _sanitize_action(
                    _extract_json_block(content), observation.attempts_remaining
                )
            except Exception as exc:
                error = str(exc)
                action = PeerReviewAction(
                    rating=5.0,
                    confidence=3.0,
                    finalize=observation.attempts_remaining <= 1,
                    metadata={"parse_error": error},
                )

            observation, reward, done, info = env.step(action)
            steps += 1
            rewards.append(reward)
            last_error = info.get("last_action_error") or error
            action_str = json.dumps(
                action.model_dump(), ensure_ascii=True, separators=(",", ":")
            )
            error_str = _single_line(last_error)
            print(
                f"[STEP] step={steps} action={action_str} reward={reward:.2f} done={str(done).lower()} error={error_str}"
            )
        success = bool(observation.best_score >= 0.9)
    finally:
        env.close()
        rewards_text = ",".join(f"{reward:.2f}" for reward in rewards)
        print(
            f"[END] success={str(success).lower()} steps={steps} rewards={rewards_text}"
        )
    return rewards


if __name__ == "__main__":
    for task_name in TASK_ORDER:
        run_task(task_name)
