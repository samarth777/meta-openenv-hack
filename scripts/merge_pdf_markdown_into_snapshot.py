"""Merge Modal-produced markdown back into the OpenReview snapshot."""

from __future__ import annotations

import json
from pathlib import Path


SNAPSHOT_PATH = Path("peer_review_env") / "data_snapshot.json"
MARKDOWN_PATH = Path("artifacts") / "pdf_markdown.json"


def main() -> None:
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    markdown_rows = json.loads(MARKDOWN_PATH.read_text(encoding="utf-8"))
    markdown_by_forum = {
        row["forum_id"]: row["paper_markdown"] for row in markdown_rows
    }

    updated = 0
    for task in snapshot.values():
        forum = task["forum"]
        forum_id = forum["forum_id"]
        if forum_id in markdown_by_forum:
            forum["paper_markdown"] = markdown_by_forum[forum_id]
            updated += 1

    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"Updated {updated} tasks in {SNAPSHOT_PATH}")


if __name__ == "__main__":
    main()
