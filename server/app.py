"""Compatibility wrapper that re-exports the real app entrypoint."""

from peer_review_env.server.app import app as app
from peer_review_env.server.app import main as _real_main


def main(host: str = "0.0.0.0", port: int = 8000):
    _real_main(host=host, port=port)


if __name__ == "__main__":
    main()
