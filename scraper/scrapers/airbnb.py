"""Airbnb careers scraper (Canada / Software Engineering department jobs).

careers.airbnb.com is a custom front-end, but its job-detail "Apply Now"
embed points at Greenhouse (board token "airbnb") — the public Board API is
used directly, a single unauthenticated GET returns every current job in one
response, no pagination needed. See CLAUDE.md's "Airbnb, Databricks, Stripe
scraping approach" section (Airbnb bullet) for how this was found.

- Greenhouse's public Board API has no server-side location filter
  (`location=` query params are silently ignored) — Canada is filtered
  client-side on `location.name`.
- Category scoping uses Greenhouse's real department id for "Software
  Engineering" (77), confirmed against the board's own `/departments`
  endpoint, via each job's top-level `departments[]` array.
- As of the CLAUDE.md investigation, 0 jobs matched Canada + Software
  Engineering simultaneously (Canada jobs exist at Airbnb, just not in this
  department right now) — an empty result here is expected, not a scraper
  bug.
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BOARD_TOKEN = "airbnb"
JOBS_URL = f"https://boards-api.greenhouse.io/v1/boards/{BOARD_TOKEN}/jobs"
SOFTWARE_ENGINEERING_DEPARTMENT_ID = 77


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=30) as client:
        response = client.get(JOBS_URL, params={"content": "true"})
        response.raise_for_status()
        raw_jobs = response.json()["jobs"]

    jobs: list[NormalizedJob] = []
    for raw in raw_jobs:
        dept_ids = {d["id"] for d in raw.get("departments") or []}
        if SOFTWARE_ENGINEERING_DEPARTMENT_ID not in dept_ids:
            continue
        location = raw.get("location", {}).get("name", "")
        if "canada" not in location.lower():
            continue
        jobs.append(_normalize(raw, location))

    logger.info("Airbnb: fetched %d jobs (of %d total on the board)", len(jobs), len(raw_jobs))
    return jobs


def _normalize(raw: dict, location: str) -> NormalizedJob:
    posted_date = raw.get("first_published")
    return {
        "external_id": str(raw["id"]),
        "title": raw["title"],
        "url": raw["absolute_url"],
        "location": location,
        "category": "Software Engineering",
        "posted_date": posted_date[:10] if posted_date else None,
        "platform": "Greenhouse",
    }
