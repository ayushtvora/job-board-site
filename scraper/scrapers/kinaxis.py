"""Kinaxis careers scraper, scoped to Canada + Engineering / Information Technology.

Kinaxis' careers site `join.kinaxis.com` is an iCIMS "Jibe" front-end
(job URLs `/jobs/<reqId>?lang=en-us`; apply links go to
`careers-kinaxis.icims.com`). Jibe serves the listing as JSON:
`GET https://join.kinaxis.com/api/jobs?page=N&internal=false` — no auth, 10
jobs per page, `totalCount` in the response (113 jobs, 2026-09-25).

- Filtered client-side: `country_code == "CA"` (50 jobs) and `category`
  (a list like `[" Engineering"]`, note the leading space) in Engineering /
  Information Technology (30 jobs).
- Fields: `req_id` (stable, = iCIMS requisition ID, external_id), `title`,
  `full_location`, `posted_date` (ISO datetime), `slug` for the job URL.
- `platform` = "iCIMS" (`ats_code` on every job).
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

LIST_URL = "https://join.kinaxis.com/api/jobs"
JOB_URL_TEMPLATE = "https://join.kinaxis.com/jobs/{slug}?lang=en-us"
CATEGORIES = {"Engineering", "Information Technology"}
COUNTRY_CODE = "CA"
MAX_PAGES = 60


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen = 0
    total = 0

    with httpx.Client(timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as client:
        for page in range(1, MAX_PAGES + 1):
            response = client.get(LIST_URL, params={"page": page, "internal": "false"})
            response.raise_for_status()
            payload = response.json()
            total = payload.get("totalCount", 0)
            page_jobs = [entry["data"] for entry in payload.get("jobs") or []]
            if not page_jobs:
                break
            seen += len(page_jobs)
            jobs.extend(_normalize(raw) for raw in page_jobs if _matches(raw))
            if seen >= total:
                break
        else:
            logger.warning("Kinaxis scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Kinaxis: fetched %d matching jobs (of %d total)", len(jobs), total)
    return jobs


def _categories(raw: dict) -> list[str]:
    return [c.strip() for c in raw.get("category") or []]


def _matches(raw: dict) -> bool:
    return raw.get("country_code") == COUNTRY_CODE and any(c in CATEGORIES for c in _categories(raw))


def _normalize(raw: dict) -> NormalizedJob:
    posted = raw.get("posted_date")
    return {
        "external_id": str(raw["req_id"]),
        "title": raw["title"].strip(),
        "url": JOB_URL_TEMPLATE.format(slug=raw["slug"]),
        "location": raw.get("full_location") or "",
        "category": ", ".join(_categories(raw)),
        "posted_date": posted[:10] if posted else None,
        "platform": "iCIMS",
    }
