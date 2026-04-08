---
title: OpenReview Score Prediction Benchmark
emoji: 📄
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
---

# OpenReview Score Prediction Benchmark

An OpenEnv environment for predicting OpenReview scores from full paper markdown.
Each task provides a full paper converted from PDF to markdown and asks the model to predict the mean human `rating` and `confidence` from OpenReview reviews.

## Overview

This benchmark uses public NeurIPS 2023 papers and reviews from OpenReview.
The runtime data source is `peer_review_env/data_snapshot.json`, which stores:

- full paper markdown extracted from the paper PDF
- raw OpenReview reviews
- ground-truth mean rating
- ground-truth mean confidence
- review count and decision

## Observation Space

`PeerReviewObservation` includes:

- `task_id`, `task_name`, `difficulty`
- `objective`
- `paper_markdown`
- `attempts_remaining`
- `current_score`, `best_score`
- `score_breakdown`
- `feedback`

## Action Space

`PeerReviewAction` includes:

- `rating` in `[1, 10]`
- `confidence` in `[1, 5]`
- `finalize`

## Tasks

1. `neurips23_easy_online_pca`
2. `neurips23_medium_erm`
3. `neurips23_hard_ip_omp`

These span easy to hard based on how predictable the final review scores are from the paper alone.

## Grading

The grader is deterministic and depends only on score prediction accuracy.

- `rating_score`: closeness to mean human rating
- `confidence_score`: closeness to mean human confidence
- `overall_score = 0.7 * rating_score + 0.3 * confidence_score`

## Reward Function

The reward is shaped over the trajectory:

- reward for improving the best prediction so far
- small per-step penalty
- repeated-prediction penalty
- weak-finalization penalty

## Setup

```bash
uv venv .venv
uv sync
uv run openenv validate .
uv run server
```

## Docker

```bash
docker build -t peer-review-env .
docker run -p 8000:8000 peer-review-env
```

## Inference

`inference.py` is at the project root and uses the OpenAI client.

Required environment variables:

- `HF_TOKEN`
- `API_BASE_URL` default: `https://api.openai.com/v1`
- `MODEL_NAME` default: `gpt-4.1-mini`

Run:

```bash
HF_TOKEN=... uv run python inference.py
```

## Rebuilding Data

To rebuild `peer_review_env/data_snapshot.json` from OpenReview:

```bash
OPENREVIEW_USERNAME=... OPENREVIEW_PASSWORD=... uv run python scripts/mint_openreview_token.py
OPENREVIEW_TOKEN=... uv run python scripts/build_openreview_snapshot.py
```

The snapshot builder uses the OpenReview API client, downloads each paper PDF, converts it to full markdown, and stores the OpenReview ground-truth score aggregates.

The deployed Hugging Face Space does not require OpenReview credentials at runtime.
It serves only the bundled static snapshot already stored in `peer_review_env/data_snapshot.json`.
