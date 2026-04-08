"""Mint a reusable OpenReview bearer token for rate-limit-safe API access."""

from __future__ import annotations

import os

import openreview


def main() -> None:
    username = os.environ.get("OPENREVIEW_USERNAME")
    password = os.environ.get("OPENREVIEW_PASSWORD")
    if not username or not password:
        raise ValueError("OPENREVIEW_USERNAME and OPENREVIEW_PASSWORD are required")

    expires_in = int(os.environ.get("OPENREVIEW_TOKEN_EXPIRES_IN", "604800"))
    expires_in = max(60, min(expires_in, 604800))
    client = openreview.api.OpenReviewClient(
        baseurl="https://api2.openreview.net",
        username=username,
        password=password,
        tokenExpiresIn=expires_in,
    )
    print("OPENREVIEW_TOKEN=" + client.token)


if __name__ == "__main__":
    main()
