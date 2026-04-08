"""Prepare a Modal input manifest from locally cached OpenReview PDFs."""

from __future__ import annotations

import json
from pathlib import Path


PDF_DIR = Path("artifacts") / "openreview_pdfs"
OUTPUT_PATH = Path("artifacts") / "pdf_manifest.json"


def main() -> None:
    entries = [
        {"forum_id": pdf_path.stem, "pdf_path": str(pdf_path)}
        for pdf_path in sorted(PDF_DIR.glob("*.pdf"))
    ]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} with {len(entries)} entries")


if __name__ == "__main__":
    main()
