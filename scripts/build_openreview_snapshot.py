"""Build a deterministic local snapshot from OpenReview using the official client.

This follows the documented API usage from OpenReview:
- install `openreview-py`
- authenticate with `openreview.api.OpenReviewClient`
- fetch notes via `get_note()` and `get_all_notes()`
- fetch PDFs via `get_pdf()` and convert them to markdown

Supported environment variables:
- `OPENREVIEW_TOKEN` preferred for repeated runs
- `OPENREVIEW_USERNAME`
- `OPENREVIEW_PASSWORD`
- `OPENREVIEW_TOKEN_EXPIRES_IN` optional token lifetime in seconds, max 1 week

Notes:
- OpenReview applies login rate limits, so avoid repeatedly logging in with username/password.
- Preferred flow: mint a token once, then reuse `OPENREVIEW_TOKEN` for subsequent runs.
- The script authenticates once and reuses the same client for all target forums.

Output:
- `peer_review_env/data_snapshot.json`
- cached PDFs under `artifacts/openreview_pdfs/`
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from statistics import mean
from typing import Any

import jwt
import openreview
import pymupdf4llm


VENUE_ID = os.environ.get("OPENREVIEW_VENUE_ID", "NeurIPS.cc/2023/Conference")
DEFAULT_PAPER_LIMIT = int(os.environ.get("OPENREVIEW_PAPER_LIMIT", "100"))
PDF_CACHE_DIR = Path("artifacts") / "openreview_pdfs"


def _parse_numeric_prefix(raw_value: str | None) -> float | None:
    if not raw_value:
        return None
    raw_value = raw_value.strip()
    if not raw_value:
        return None
    prefix = raw_value.split(":", 1)[0].strip()
    try:
        return float(prefix)
    except ValueError:
        return None


def _content_value(note, key: str) -> str | None:
    field = note.content.get(key)
    if field is None:
        return None
    if isinstance(field, dict):
        value = field.get("value")
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return None if value is None else str(value)
    return str(field)


def _review_payload(note) -> dict[str, object]:
    return {
        "id": note.id,
        "forum": note.forum,
        "replyto": note.replyto,
        "signatures": list(note.signatures or []),
        "summary": _content_value(note, "summary"),
        "strengths": _content_value(note, "strengths"),
        "weaknesses": _content_value(note, "weaknesses"),
        "questions": _content_value(note, "questions"),
        "limitations": _content_value(note, "limitations"),
        "rating": _content_value(note, "rating"),
        "confidence": _content_value(note, "confidence"),
        "presentation": _content_value(note, "presentation"),
        "soundness": _content_value(note, "soundness"),
        "contribution": _content_value(note, "contribution"),
    }


def _pdf_bytes_to_markdown(pdf_bytes: bytes) -> str:
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as handle:
        handle.write(pdf_bytes)
        handle.flush()
        return pymupdf4llm.to_markdown(handle.name)


def _difficulty_for_index(index: int, total: int) -> str:
    if total <= 3:
        return ("easy", "medium", "hard")[min(index, 2)]
    ratio = index / max(1, total - 1)
    if ratio < 0.34:
        return "easy"
    if ratio < 0.67:
        return "medium"
    return "hard"


def _task_id_from_note(index: int, note) -> str:
    number = note.number if getattr(note, "number", None) is not None else index + 1
    return f"neurips23_paper_{int(number):04d}"


def _load_target_forums(
    client: openreview.api.OpenReviewClient, limit: int
) -> list[dict[str, Any]]:
    notes = client.get_all_notes(content={"venueid": VENUE_ID})
    notes = sorted(notes, key=lambda note: (getattr(note, "number", 10**9), note.id))[
        :limit
    ]
    total = len(notes)
    return [
        {
            "task_id": _task_id_from_note(index, note),
            "task_name": f"Predict scores for '{note.content['title']['value']}'",
            "difficulty": _difficulty_for_index(index, total),
            "source_url": f"https://openreview.net/forum?id={note.id}",
            "forum_id": note.id,
        }
        for index, note in enumerate(notes)
    ]


def _get_or_fetch_pdf_bytes(
    client: openreview.api.OpenReviewClient, forum_id: str
) -> bytes:
    PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = PDF_CACHE_DIR / f"{forum_id}.pdf"
    if pdf_path.exists():
        return pdf_path.read_bytes()
    pdf_bytes = client.get_pdf(forum_id)
    pdf_path.write_bytes(pdf_bytes)
    return pdf_bytes


def _decision_payload(note) -> dict[str, object]:
    return {
        "id": note.id,
        "decision": _content_value(note, "decision"),
        "comment": _content_value(note, "comment"),
    }


def _fetch_forum_snapshot(
    client: openreview.api.OpenReviewClient, forum_id: str
) -> dict[str, object]:
    paper = client.get_note(forum_id)
    forum_notes = client.get_all_notes(forum=forum_id)
    pdf_bytes = _get_or_fetch_pdf_bytes(client, forum_id)
    paper_markdown = _pdf_bytes_to_markdown(pdf_bytes)

    reviews = []
    decisions = []
    rebuttals = []
    comments = []
    for note in forum_notes:
        invitations = list(note.invitations or [])
        if any(invitation.endswith("Official_Review") for invitation in invitations):
            reviews.append(_review_payload(note))
        elif any(invitation.endswith("Decision") for invitation in invitations):
            decisions.append(_decision_payload(note))
        elif any(
            invitation.endswith("Author_Rebuttal") or invitation.endswith("Rebuttal")
            for invitation in invitations
        ):
            rebuttals.append(
                {
                    "id": note.id,
                    "replyto": note.replyto,
                    "rebuttal": _content_value(note, "rebuttal"),
                    "pdf": _content_value(note, "pdf"),
                }
            )
        else:
            comments.append(
                {
                    "id": note.id,
                    "replyto": note.replyto,
                    "title": _content_value(note, "title"),
                    "comment": _content_value(note, "comment"),
                }
            )

    rating_values = [_parse_numeric_prefix(review.get("rating")) for review in reviews]
    rating_values = [value for value in rating_values if value is not None]
    confidence_values = [
        _parse_numeric_prefix(review.get("confidence")) for review in reviews
    ]
    confidence_values = [value for value in confidence_values if value is not None]

    return {
        "forum_id": paper.id,
        "title": _content_value(paper, "title"),
        "authors": paper.content.get("authors", {}).get("value", []),
        "abstract": _content_value(paper, "abstract"),
        "tldr": _content_value(paper, "TLDR"),
        "keywords": paper.content.get("keywords", {}).get("value", []),
        "venue": _content_value(paper, "venue"),
        "venueid": _content_value(paper, "venueid"),
        "pdf": _content_value(paper, "pdf"),
        "cached_pdf_path": str(PDF_CACHE_DIR / f"{forum_id}.pdf"),
        "paper_markdown": paper_markdown,
        "reviews": reviews,
        "decisions": decisions,
        "rebuttals": rebuttals,
        "comments": comments,
        "review_count": len(reviews),
        "decision_count": len(decisions),
        "rating_mean": round(mean(rating_values), 4) if rating_values else None,
        "confidence_mean": round(mean(confidence_values), 4)
        if confidence_values
        else None,
    }


def _is_token_usable(token: str) -> bool:
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except Exception:
        return False

    exp = payload.get("exp")
    if exp is None:
        return True

    import time

    return float(exp) > (time.time() + 30)


def _build_client() -> tuple[openreview.api.OpenReviewClient, str | None]:
    token = os.environ.get("OPENREVIEW_TOKEN")
    if token and _is_token_usable(token):
        client = openreview.api.OpenReviewClient(
            baseurl="https://api2.openreview.net",
            token=token,
        )
        return client, token

    username = os.environ.get("OPENREVIEW_USERNAME")
    password = os.environ.get("OPENREVIEW_PASSWORD")
    if not username or not password:
        raise ValueError(
            "Provide OPENREVIEW_TOKEN or both OPENREVIEW_USERNAME and OPENREVIEW_PASSWORD"
        )

    expires_in = int(os.environ.get("OPENREVIEW_TOKEN_EXPIRES_IN", "604800"))
    expires_in = max(60, min(expires_in, 604800))
    client = openreview.api.OpenReviewClient(
        baseurl="https://api2.openreview.net",
        username=username,
        password=password,
        tokenExpiresIn=expires_in,
    )
    return client, client.token


def main() -> None:
    client, token = _build_client()
    target_forums = _load_target_forums(client, DEFAULT_PAPER_LIMIT)

    snapshot: dict[str, object] = {}
    for task in target_forums:
        task_id = task["task_id"]
        print(f"Fetching {task_id} :: {task['forum_id']}")
        snapshot[task_id] = {
            "task_name": task["task_name"],
            "difficulty": task["difficulty"],
            "source_url": task["source_url"],
            "forum": _fetch_forum_snapshot(client, task["forum_id"]),
        }

    output_path = Path("peer_review_env") / "data_snapshot.json"
    output_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
