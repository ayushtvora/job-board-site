"""Spotify careers scraper, scoped to Canada + Engineering.

lifeatspotify.com's own API only does client-side filtering and is a thin
wrapper; the real backend ATS is Lever, confirmed via each job's `apply`
link pointing at `jobs.lever.co/spotify/...`. See CLAUDE.md's "Intel,
Oracle, Spotify, Adobe, Sony, AMD, Uber scraping approach" section (Spotify
bullet) for how this was found.

- `GET https://api.lever.co/v0/postings/spotify?mode=json` returns the full
  current posting list in one call (~71 postings at investigation time) —
  no pagination needed at this size, though `skip=` exists on Lever's API
  if that ever changes.
- No server-side Canada/category filter — each posting carries `country`
  (ISO-2, e.g. "CA") and `categories.department`, filtered client-side here.
- CLAUDE.md documents 0 real Canada + Engineering matches at investigation
  time (the one Canada posting found was department "Data and Analytics",
  not Engineering) — a legitimate empty result, not a bug.
"""

import logging
from datetime import datetime, timezone

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

LIST_URL = "https://api.lever.co/v0/postings/spotify"

COUNTRY_CODE = "CA"
CATEGORY_KEYWORD = "engineering"


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []

    with httpx.Client(timeout=30) as client:
        response = client.get(LIST_URL, params={"mode": "json"})
        response.raise_for_status()
        postings = response.json()

        for raw in postings:
            if raw.get("country") != COUNTRY_CODE:
                continue
            department = (raw.get("categories") or {}).get("department") or ""
            if CATEGORY_KEYWORD not in department.lower():
                continue
            jobs.append(_normalize(raw))

    logger.info("Spotify: fetched %d Canada + Engineering jobs (of %d total postings)", len(jobs), len(postings))
    return jobs


def _normalize(raw: dict) -> NormalizedJob:
    categories = raw.get("categories") or {}
    created_at = raw.get("createdAt")
    posted_date = None
    if created_at:
        posted_date = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

    return {
        "external_id": raw["id"],
        "title": raw["text"],
        "url": raw.get("hostedUrl", ""),
        "location": categories.get("location", ""),
        "category": categories.get("department", ""),
        "posted_date": posted_date,
        "platform": "Lever",
    }
