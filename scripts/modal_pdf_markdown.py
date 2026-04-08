"""Parallel PDF-to-markdown extraction with Modal.

Usage:
1. Authenticate Modal once:
   uv run modal token new

2. Run a batch extraction over cached PDFs:
   uv run modal run scripts/modal_pdf_markdown.py::extract_batch --input-manifest artifacts/pdf_manifest.json --output artifacts/pdf_markdown.json

The manifest format is a JSON array of objects like:
[{"forum_id": "abc123", "pdf_path": "artifacts/openreview_pdfs/abc123.pdf"}]
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import modal


app = modal.App("peer-review-pdf-markdown")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("tesseract-ocr")
    .pip_install("pymupdf4llm", "pymupdf")
)


@app.function(image=image, cpu=2, memory=4096, timeout=1800)
def extract_pdf_markdown(item: dict[str, str]) -> dict[str, str]:
    import pymupdf4llm

    pdf_path = item["pdf_path"]
    forum_id = item["forum_id"]
    pdf_bytes = Path(pdf_path).read_bytes()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as handle:
        handle.write(pdf_bytes)
        handle.flush()
        markdown = pymupdf4llm.to_markdown(handle.name)
    return {"forum_id": forum_id, "paper_markdown": markdown}


@app.local_entrypoint()
def extract_batch(input_manifest: str, output: str = "artifacts/pdf_markdown.json"):
    manifest = json.loads(Path(input_manifest).read_text(encoding="utf-8"))
    results = list(extract_pdf_markdown.map(manifest, order_outputs=True))
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {output_path}")
