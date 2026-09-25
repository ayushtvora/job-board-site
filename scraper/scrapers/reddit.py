"""Reddit careers scraper (Canada / Engineering department jobs).

job-boards.greenhouse.io/reddit is Greenhouse's own hosted board — the
public Board API is used directly, a single unauthenticated GET returns
every current job in one response, no pagination needed. See CLAUDE.md's
"Liberty Mutual, Blizzard, Riot Games, Nvidia, UBC, Reddit, ATS Corporation
scraping approach" section (Reddit bullet) for how this was found.

- Greenhouse's public Board API has no server-side location filter
  (`location=` query params are silently ignored, confirmed by diffing
  filtered vs. unfiltered responses) — Canada is filtered client-side on
  `location.name`.
- Category scoping uses Greenhouse's real department tree
  (`GET .../departments`) rather than string-matching: the top-level
  "Engineering" department (id 16253) plus its child departments (Ads
  Engineering, Machine Learning, BE Platform, Site Reliability, FE
  Platform, etc., listed in its `child_ids`). Each job's own top-level
  `departments[]` array is checked against that id set. The `metadata[]`
  entry literally named "Department" is NOT used — CLAUDE.md notes it's
  unreliable/null on real jobs.
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BOARD_TOKEN = "reddit"
JOBS_URL = f"https://boards-api.greenhouse.io/v1/boards/{BOARD_TOKEN}/jobs"
DEPARTMENTS_URL = f"https://boards-api.greenhouse.io/v1/boards/{BOARD_TOKEN}/departments"
ENGINEERING_DEPARTMENT_NAME = "Engineering"


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=30) as client:
        dept_response = client.get(DEPARTMENTS_URL)
        dept_response.raise_for_status()
        engineering_ids = _engineering_department_ids(dept_response.json()["departments"])

        jobs_response = client.get(JOBS_URL, params={"content": "true"})
        jobs_response.raise_for_status()
        raw_jobs = jobs_response.json()["jobs"]

    jobs: list[NormalizedJob] = []
    for raw in raw_jobs:
        dept_ids = {d["id"] for d in raw.get("departments") or []}
        if not dept_ids & engineering_ids:
            continue
        location = raw.get("location", {}).get("name", "")
        if "canada" not in location.lower():
            continue
        jobs.append(_normalize(raw, location))

    logger.info("Reddit: fetched %d jobs (of %d total on the board)", len(jobs), len(raw_jobs))
    return jobs


def _engineering_department_ids(departments: list[dict]) -> set[int]:
    for dept in departments:
        if dept["name"] == ENGINEERING_DEPARTMENT_NAME:
            return {dept["id"]} | set(dept.get("child_ids") or [])
    raise ValueError(f"Could not find a '{ENGINEERING_DEPARTMENT_NAME}' department on Reddit's board — structure may have changed")


def _normalize(raw: dict, location: str) -> NormalizedJob:
    posted_date = raw.get("first_published")
    departments = ", ".join(d["name"] for d in raw.get("departments") or [])
    return {
        "external_id": str(raw["id"]),
        "title": raw["title"],
        "url": raw["absolute_url"],
        "location": location,
        "category": departments,
        "posted_date": posted_date[:10] if posted_date else None,
        "platform": "Greenhouse",
    }
