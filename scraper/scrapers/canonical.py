"""Canonical careers scraper, scoped to Canada + Engineering (heuristic, best-effort).

canonical.com/careers embeds job-boards.greenhouse.io/canonical/jobs/<id>
links directly — Greenhouse, confirmed. See CLAUDE.md's "Meta, Amazon,
Google, Apple, Microsoft, IBM, Canonical scraping approach" section
(Canonical bullet) for how this was found.

- `GET /v1/boards/canonical/jobs?content=true` returns the entire current
  job list in one response — no pagination needed.
- No single "Software Engineering" department exists; Canonical's tree has
  separate sub-departments instead (confirmed via
  `GET /v1/boards/canonical/departments`), including "Charm Engineering",
  "Cloud Engineering", "Devices Engineering", "Engineering Fast Track",
  "Excellence Engineering", "Field Engineering", "SaaS Engineering", "SRE",
  "Support Engineering", "Ubuntu Engineering", and "Web Engineering". Rather
  than hardcode that whole list, a job is treated as Engineering-scoped if
  any of its departments' names contain "engineering" (case-insensitive) or
  equal "SRE" exactly — this matches the confirmed set above without
  needing to keep an exhaustive list in sync.
- Canada matching is fuzzy and, per CLAUDE.md, a known data-shape
  limitation rather than a bug to fix: Canonical is remote-first, so
  `location.name` (a "; "-joined list of `offices[].name`) is almost never
  a bare country name. There is exactly one literal on-site office,
  "Office Based - Toronto, Canada", which this scraper matches directly.
  Deliberately NOT matched here: the much broader "Home Based - Americas"
  bucket, which also covers US and Latin America remote hires and would
  vastly overcount if treated as "Canada" (confirmed ~30+ jobs carry that
  label vs. ~2 for the literal Toronto office). The tradeoff: this scraper
  undercounts real Canada-based remote engineers filed under "Home Based -
  Americas" with no country-level field to disambiguate them further from
  the public API — a floor on the true count, not an exact figure.
- `first_published` is the true original posting date (confirmed distinct
  from `updated_at`).
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BOARD_TOKEN = "canonical"
JOBS_URL = f"https://boards-api.greenhouse.io/v1/boards/{BOARD_TOKEN}/jobs"

# Literal on-site office string for Canada — see the fuzzy-matching caveat
# in the module docstring for why the broader "Home Based - Americas"
# bucket is intentionally excluded.
CANADA_OFFICE = "Office Based - Toronto, Canada"


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=30) as client:
        response = client.get(JOBS_URL, params={"content": "true"})
        response.raise_for_status()
        raw_jobs = response.json()["jobs"]

    jobs = [raw for raw in raw_jobs if _is_engineering(raw) and _is_canada(raw)]

    logger.info(
        "Canonical: fetched %d matching jobs (of %d total; Canada matching is a "
        "floor, not exact — see module docstring)",
        len(jobs),
        len(raw_jobs),
    )
    return [_normalize(raw) for raw in jobs]


def _is_engineering(raw: dict) -> bool:
    for dept in raw.get("departments", []):
        name = dept["name"]
        if "engineering" in name.lower() or name == "SRE":
            return True
    return False


def _is_canada(raw: dict) -> bool:
    return CANADA_OFFICE in raw["location"]["name"]


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
