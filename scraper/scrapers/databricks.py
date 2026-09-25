"""Databricks careers scraper, scoped to Canada + Engineering (incl. Engineering - Pipeline).

Databricks' public-facing careers site is a Gatsby front-end, but every job
is really served by Greenhouse's public Board API — confirmed via the site's
`page-data.json` embedding a `allGreenhouseJob` GraphQL type and `gh_jid=`
job URLs. See CLAUDE.md's "Airbnb, Databricks, Stripe scraping approach"
section for how this was found.

- `GET /v1/boards/databricks/jobs?content=true` returns the entire current
  job list in one response — no pagination needed.
- Greenhouse's public API has no server-side location filter, so Canada is
  matched client-side on each job's `location.name` containing "Canada".
- Two departments are the SWE-relevant scope here, matched by id (names are
  stable but ids are the confirmed-durable identifier): "Engineering"
  (4001015002) and "Engineering - Pipeline" (4115423002).
- `requisition_id` is a real, reliable value for Databricks (unlike
  Stripe/Airbnb, where CLAUDE.md notes it's a placeholder) but Greenhouse's
  own `id` is used as `external_id` anyway, for consistency with the other
  Greenhouse scrapers in this codebase.
- `first_published` is the true original posting date (confirmed distinct
  from `updated_at`, which changes on any edit).
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BOARD_TOKEN = "databricks"
JOBS_URL = f"https://boards-api.greenhouse.io/v1/boards/{BOARD_TOKEN}/jobs"

# Confirmed department ids (see module docstring) — not derivable from
# department name alone since Greenhouse ids are opaque.
ENGINEERING_DEPARTMENT_IDS = {4001015002, 4115423002}


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=30) as client:
        response = client.get(JOBS_URL, params={"content": "true"})
        response.raise_for_status()
        raw_jobs = response.json()["jobs"]

    jobs = [raw for raw in raw_jobs if _is_target_department(raw) and _is_canada(raw)]

    logger.info(
        "Databricks: fetched %d matching jobs (of %d total)", len(jobs), len(raw_jobs)
    )
    return [_normalize(raw) for raw in jobs]


def _is_target_department(raw: dict) -> bool:
    return any(dept["id"] in ENGINEERING_DEPARTMENT_IDS for dept in raw.get("departments", []))


def _is_canada(raw: dict) -> bool:
    return "canada" in raw["location"]["name"].lower()


def _normalize(raw: dict) -> NormalizedJob:
    departments = ", ".join(dept["name"] for dept in raw.get("departments", []))
    posted_date = raw.get("first_published")
    return {
        "external_id": str(raw["id"]),
        "title": raw["title"],
        "url": raw["absolute_url"],
        "location": raw["location"]["name"],
        "category": departments,
        "posted_date": posted_date[:10] if posted_date else None,
        "platform": "Greenhouse",
    }
