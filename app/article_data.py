"""Read the locally mirrored article archive."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "clerk_articles.json"


@lru_cache(maxsize=1)
def load_articles() -> tuple[dict, ...]:
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return tuple(payload["articles"])


@lru_cache(maxsize=1)
def article_map() -> dict[str, dict]:
    return {article["slug"]: article for article in load_articles()}


def get_article(slug: str) -> dict | None:
    return article_map().get(slug)


def article_slugs() -> tuple[str, ...]:
    return tuple(article["slug"] for article in load_articles())
