"""Blizzard careers scraper (Engineering & Technology category, Canada only).

Same Phenom People platform as RBC/BMO (scrapers/rbc.py, scrapers/bmo.py) —
job data is embedded server-side in a `phApp.ddo = {...}` JSON blob, so a
plain HTTP GET is enough, no browser needed. See rbc.py's docstring for the
general shape of this approach.

Blizzard-specific notes (see CLAUDE.md's "Liberty Mutual, Blizzard, Riot
Games, Nvidia, UBC, Reddit, ATS Corporation scraping approach" section):

- Deviation from CLAUDE.md: the job list does NOT live at
  `ddo["eagerLoadRefineSearch"]` like RBC/BMO. For this site it's at
  `ddo["targetedJobs"]` instead (`targetedJobs.totalHits` /
  `targetedJobs.data.jobs`) — confirmed live 2026-09-21. Everything else
  about the blob (per-job fields) matches RBC's shape.
- Category refinement is the query param `rk=l-engineering-technology` on
  the `engineering-technology` category page (not an opaque ID like
  Workday's facets, and not a plain `category=` label like BMO's).
- Pagination: `from=<offset>`, but the confirmed page size here is 5 (not
  RBC/BMO's 10) — first page returned `hits: 5` of `totalHits: 9`. No `s=1`
  param is sent (not documented as needed here, unlike RBC).
- **No confirmed server-side country filter** — every job's real ATS is
  Microsoft's Xbox Gaming Workday tenant (`applyUrl` points at
  `xboxgaming.wd1.myworkdayjobs.com/Blizzard_External_Careers/...`), so
  `platform` is `"Workday"` per CLAUDE.md's stated convention (record the
  real apply backend), not "Phenom". Canada filtering is done client-side
  on each job's own `country` field. CLAUDE.md notes Blizzard currently has
  **zero** Canada postings company-wide — an empty result here is expected,
  not a bug.
"""

import json
import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

CATEGORY_URL = "https://careers.blizzard.com/global/en/engineering-technology"
REFINEMENT = "l-engineering-technology"
DDO_MARKER = "phApp.ddo = "
MAX_PAGES = 50  # safety cap; this category currently has ~9 jobs total


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    offset = 0
    total_hits: int | None = None

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for _ in range(MAX_PAGES):
            response = client.get(CATEGORY_URL, params={"rk": REFINEMENT, "from": offset})
            response.raise_for_status()

            targeted = _extract_ddo(response.text)["targetedJobs"]
            total_hits = targeted["totalHits"]
            page_jobs = targeted["data"]["jobs"]
            if not page_jobs:
                break

            for raw in page_jobs:
                job_id = raw["jobId"]
                # Pagination isn't confirmed fully stable under the site's
                # default sort (same caveat as RBC), so guard against overlap.
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                if raw.get("country") != "Canada":
                    continue
                jobs.append(_normalize(raw))

            offset += len(page_jobs)
            if offset >= total_hits:
                break
        else:
            logger.warning("Blizzard scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Blizzard: fetched %d Canada jobs (site reported totalHits=%s)", len(jobs), total_hits)
    return jobs


def _extract_ddo(html: str) -> dict:
    idx = html.find(DDO_MARKER)
    if idx == -1:
        raise ValueError("Could not find phApp.ddo in Blizzard page — site structure may have changed")
    start = idx + len(DDO_MARKER)
    ddo, _end = json.JSONDecoder().raw_decode(html, start)
    return ddo


def _normalize(raw: dict) -> NormalizedJob:
    location = (
        raw.get("location")
        or ", ".join(raw.get("multi_location", []))
        or raw.get("cityStateCountry", "")
    )
    posted_date = raw.get("postedDate")
    return {
        "external_id": raw["jobId"],
        "title": raw["title"],
        "url": raw["applyUrl"],
        "location": location,
        "category": raw.get("category", ""),
        "posted_date": posted_date[:10] if posted_date else None,
        "platform": "Workday",
    }
