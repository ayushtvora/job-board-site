"""Riot Games careers scraper (Canada / Engineering jobs).

riotgames.com/en/work-with-us is a custom React site, but each job's detail
page embeds the standard Greenhouse widget (board token "riotgames"), so the
canonical data source is Greenhouse's public Board API — a single
unauthenticated GET returns every current job in one response, no pagination
needed. See CLAUDE.md's "Liberty Mutual, Blizzard, Riot Games, Nvidia, UBC,
Reddit, ATS Corporation scraping approach" section (Riot Games bullet) for
how this was found.

- Greenhouse's public Board API has no server-side location filter
  (`location=` query params are silently ignored) — Canada is filtered
  client-side on `location.name`.
- There's also no single category/department facet that maps cleanly to
  "Engineering" here; instead each job's `metadata[]` array has a `"Craft"`
  field. Confirmed values include "Software Engineering Group", "Engineering",
  "Infrastructure", "QA Group", "Data", among many non-technical ones (e.g.
  "Art", "Esports", "Finance"). This scraper treats "Software Engineering
  Group", "Engineering", and "Infrastructure" as the software-engineering-ish
  subset — "QA Group" and "Data" are adjacent but not core software
  engineering, so they're excluded.
- As of the CLAUDE.md investigation there were 0 Canada postings company-wide
  (confirmed against the site's own location dropdown) — an empty result
  here is expected, not a scraper bug.
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BOARD_TOKEN = "riotgames"
JOBS_URL = f"https://boards-api.greenhouse.io/v1/boards/{BOARD_TOKEN}/jobs"

# Craft values (from each job's metadata[]) treated as software-engineering-ish.
ENGINEERING_CRAFTS = {"Software Engineering Group", "Engineering", "Infrastructure"}


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=30) as client:
        response = client.get(JOBS_URL, params={"content": "true"})
        response.raise_for_status()
        raw_jobs = response.json()["jobs"]

    jobs: list[NormalizedJob] = []
    for raw in raw_jobs:
        craft = _get_craft(raw)
        if craft not in ENGINEERING_CRAFTS:
            continue
        location = raw.get("location", {}).get("name", "")
        if "canada" not in location.lower():
            continue
        jobs.append(_normalize(raw, craft, location))

    logger.info("Riot Games: fetched %d jobs (of %d total on the board)", len(jobs), len(raw_jobs))
    return jobs


def _get_craft(raw: dict) -> str | None:
    for entry in raw.get("metadata") or []:
        if entry.get("name") == "Craft":
            return entry.get("value")
    return None


def _normalize(raw: dict, craft: str, location: str) -> NormalizedJob:
    posted_date = raw.get("first_published")
    return {
        "external_id": str(raw["id"]),
        "title": raw["title"],
        "url": raw["absolute_url"],
        "location": location,
        "category": craft or "",
        "posted_date": posted_date[:10] if posted_date else None,
        "platform": "Greenhouse",
    }
