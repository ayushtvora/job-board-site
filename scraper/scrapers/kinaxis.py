"""Kinaxis careers scraper, scoped to Canada + Engineering / Information Technology.

Kinaxis' careers site `join.kinaxis.com` is an iCIMS "Jibe" front-end
(job URLs `/jobs/<reqId>?lang=en-us`; apply links go to
`careers-kinaxis.icims.com`), via the shared helper in scrapers/jibe.py
(113 jobs, 2026-09-25).

- Filtered client-side: `country_code == "CA"` (50 jobs) and `category`
  in Engineering / Information Technology (30 jobs).
"""

from .base import NormalizedJob, is_core_title
from .jibe import categories, scrape_jibe

CATEGORIES = {"Engineering", "Information Technology"}


def _matches(raw: dict) -> bool:
    return raw.get("country_code") == "CA" and (
        any(c in CATEGORIES for c in categories(raw)) or is_core_title(raw.get("title") or "")
    )


def scrape() -> list[NormalizedJob]:
    return scrape_jibe(name="Kinaxis", base_url="https://join.kinaxis.com", job_path="/jobs", job_filter=_matches)
