"""Shared helper for Lever postings API scrapers.

Same API as Spotify (see CLAUDE.md's "Spotify scraping approach"):
`GET https://api.lever.co/v0/postings/<company>?mode=json` is public and
unauthenticated, and returns every posting in one call (`skip=N` paging
exists but hasn't been needed).

- No server-side country or department filter, so both are matched
  client-side: `country` is an ISO-2 code per posting (e.g. "CA"), and
  `department_filter` gets `categories.department`. Jobs with a data
  title are kept whatever their department.
- Per posting: `id` (stable UUID, used as `external_id`), `text` (title),
  `categories.{department,team,location}`, `hostedUrl`, and `createdAt`
  (epoch milliseconds — a real posted date).
"""

import logging
from collections.abc import Callable
from datetime import datetime, timezone

import httpx

from .base import NormalizedJob, is_data_title

logger = logging.getLogger(__name__)


def scrape_lever(
    *,
    name: str,
    company: str,
    department_filter: Callable[[str], bool],
    country: str = "CA",
) -> list[NormalizedJob]:
    with httpx.Client(timeout=30) as client:
        response = client.get(f"https://api.lever.co/v0/postings/{company}", params={"mode": "json"})
        response.raise_for_status()
        postings = response.json()

    matched = [
        raw
        for raw in postings
        if raw.get("country") == country
        and (department_filter((raw.get("categories") or {}).get("department") or "") or is_data_title(raw["text"]))
    ]
    logger.info("%s: fetched %d matching jobs (of %d total)", name, len(matched), len(postings))
    return [_normalize(raw) for raw in matched]


def _normalize(raw: dict) -> NormalizedJob:
    categories = raw.get("categories") or {}
    created_at = raw.get("createdAt")
    return {
        "external_id": raw["id"],
        "title": raw["text"].strip(),
        "url": raw.get("hostedUrl") or "",
        "location": categories.get("location") or "",
        "category": categories.get("department") or "",
        "posted_date": datetime.fromtimestamp(created_at / 1000, tz=timezone.utc).strftime("%Y-%m-%d") if created_at else None,
        "platform": "Lever",
    }
