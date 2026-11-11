"""ICES careers scraper (all postings).

ICES (Toronto's health-data research institute, formerly the Institute
for Clinical Evaluative Sciences) posts on **BambooHR**, linked from
ices.on.ca/careers. BambooHR's careers page loads its list from
`GET https://ices.bamboohr.com/careers/list` (JSON, no auth):
`{"result": [{id, jobOpeningName, departmentLabel, location: {city, state}}]}`.
Investigated 2026-11-10: 5 postings, all Toronto, e.g. "Data Architect".

- ICES is a data organization through and through (analysts,
  epidemiologists, data architects), so every posting is kept; it's
  small enough that the odd admin role is harmless.
- The job page is `https://ices.bamboohr.com/careers/<id>`, a
  client-rendered page, so the posted date and description come from
  each posting's `GET /careers/<id>/detail` (`result.jobOpening.datePosted`
  and `.description`, HTML).
"""

import logging

import httpx

from .base import NormalizedJob, clean_description

logger = logging.getLogger(__name__)

BASE_URL = "https://ices.bamboohr.com/careers"


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=30, headers={"Accept": "application/json"}) as client:
        response = client.get(f"{BASE_URL}/list")
        response.raise_for_status()
        postings = response.json()["result"]

        details = {
            raw["id"]: client.get(f"{BASE_URL}/{raw['id']}/detail").raise_for_status().json()["result"]["jobOpening"]
            for raw in postings
        }

    jobs = []
    for raw in postings:
        detail = details[raw["id"]]
        location = raw.get("location") or {}
        place = ", ".join(part for part in (location.get("city"), location.get("state"), "Canada") if part)
        jobs.append(
            {
                "external_id": str(raw["id"]),
                "title": raw["jobOpeningName"].strip(),
                "url": f"{BASE_URL}/{raw['id']}",
                "location": place,
                "category": raw.get("departmentLabel") or "",
                "posted_date": detail.get("datePosted"),
                "platform": "BambooHR",
                "description": clean_description(detail.get("description")),
            }
        )
    logger.info("ICES: fetched %d jobs", len(jobs))
    return jobs
