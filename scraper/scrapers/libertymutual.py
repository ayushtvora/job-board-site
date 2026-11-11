"""Liberty Mutual careers scraper, scoped to Canada + Technology, plus data roles.

Real careers URL is `https://searchjobs.libertymutualgroup.com/careers`,
running on Eightfold (confirmed via `X-EF-NS`/`X-EF-CID` response headers).
See CLAUDE.md's "Liberty Mutual, Blizzard, Riot Games, Nvidia, UBC, Reddit,
ATS Corporation scraping approach" section (Liberty Mutual bullet) for how
this was found.

- Public JSON API: `GET .../api/apply/v2/jobs?domain=libertymutual.com&start=0&num=<N>&query=`.
  `domain` must be `libertymutual.com`, **not** `libertymutualgroup.com` (the
  latter silently returns a generic 404-shell rather than an HTTP error).
- `location=` and `department=` query params are real, server-side filters —
  confirmed working (e.g. `department=Technology&location=Canada`). Only
  `location` is sent: the department is checked client-side so that data
  titles from other departments are kept too.
- Pagination via `start`/`num`.
- CLAUDE.md documents 0 current Canada + Technology matches at investigation
  time — a legitimate empty result (this company has real jobs elsewhere,
  just not in this filter combination right now), not a bug.
"""

import logging
from datetime import datetime, timezone

import httpx

from .base import NormalizedJob, is_core_title

logger = logging.getLogger(__name__)

LIST_URL = "https://searchjobs.libertymutualgroup.com/api/apply/v2/jobs"
DOMAIN = "libertymutual.com"  # not "libertymutualgroup.com" — see module docstring
LOCATION_FILTER = "Canada"
DEPARTMENT_FILTER = "Technology"

PAGE_SIZE = 50
MAX_PAGES = 50  # safety cap; this filter currently has 0 jobs


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    start = 0
    total: int | None = None

    with httpx.Client(timeout=30) as client:
        for _ in range(MAX_PAGES):
            response = client.get(
                LIST_URL,
                params={
                    "domain": DOMAIN,
                    "start": start,
                    "num": PAGE_SIZE,
                    "query": "",
                    "location": LOCATION_FILTER,
                },
            )
            response.raise_for_status()
            payload = response.json()
            if total is None:
                total = payload.get("count", 0)
            positions = payload.get("positions") or []
            if not positions:
                break

            for raw in positions:
                job_id = raw["display_job_id"]
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                if raw.get("department") == DEPARTMENT_FILTER or is_core_title(raw.get("name") or ""):
                    jobs.append(_normalize(raw))

            start += PAGE_SIZE
            if start >= total:
                break
        else:
            logger.warning("Liberty Mutual scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Liberty Mutual: fetched %d jobs (site reported count=%s)", len(jobs), total)
    return jobs


def _normalize(raw: dict) -> NormalizedJob:
    location = raw.get("location") or ", ".join(raw.get("locations") or [])
    t_create = raw.get("t_create")
    posted_date = None
    if t_create:
        posted_date = datetime.fromtimestamp(t_create, tz=timezone.utc).strftime("%Y-%m-%d")

    return {
        "external_id": raw["display_job_id"],
        "title": raw["name"],
        "url": raw.get("canonicalPositionUrl", ""),
        "location": location,
        "category": raw.get("department", ""),
        "posted_date": posted_date,
        "platform": "Eightfold",
    }
