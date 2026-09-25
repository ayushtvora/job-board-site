"""Stripe careers scraper, scoped to Canada + Engineering (heuristic match).

Stripe's public-facing careers site is custom-built, but embeds an inline
JSON blob with `"listings":[{"greenhouseId":...}]` per job — the real ATS is
Greenhouse. See CLAUDE.md's "Airbnb, Databricks, Stripe scraping approach"
section for how this was found.

- `GET /v1/boards/stripe/jobs?content=true` returns the entire current job
  list in one response — no pagination needed.
- Greenhouse's public API has no server-side location filter, so Canada is
  matched client-side on each job's `location.name` containing "Canada".
- Unlike Databricks/Riot/Reddit, Stripe has no single "Engineering"
  department to match by id — its department tree is ~192 deeply nested,
  numeric-prefixed teams (e.g. "8512 Terminal - Eng"). Per CLAUDE.md's
  recommended heuristic, a job counts as Engineering-scoped if any of its
  departments' names contain "eng" (case-insensitive, catches "- Eng" /
  "Engineering" suffixes) or its title contains "engineer". This is a
  heuristic, not an exact facet — confirmed by CLAUDE.md to land ~29 Canada
  matches when investigated; the live count may drift.
- `requisition_id` is an unreliable placeholder for Stripe (always literal
  "See Opening ID", confirmed in CLAUDE.md) — Greenhouse's own `id` is used
  as `external_id` instead.
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BOARD_TOKEN = "stripe"
JOBS_URL = f"https://boards-api.greenhouse.io/v1/boards/{BOARD_TOKEN}/jobs"


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=30) as client:
        response = client.get(JOBS_URL, params={"content": "true"})
        response.raise_for_status()
        raw_jobs = response.json()["jobs"]

    jobs = [raw for raw in raw_jobs if _is_engineering(raw) and _is_canada(raw)]

    logger.info(
        "Stripe: fetched %d matching jobs (of %d total)", len(jobs), len(raw_jobs)
    )
    return [_normalize(raw) for raw in jobs]


def _is_engineering(raw: dict) -> bool:
    if "engineer" in raw["title"].lower():
        return True
    return any("eng" in dept["name"].lower() for dept in raw.get("departments", []))


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
