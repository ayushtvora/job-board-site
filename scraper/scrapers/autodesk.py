"""Autodesk careers scraper, scoped to Canada + tech job categories.

Autodesk has moved its careers site to **Eightfold** at
`jobs.autodesk.com/careers`, found 2026-09-25 (confirmed by `X-EF-*` response
headers). Its old Workday site (`autodesk.wd1.myworkdayjobs.com/Ext`) now
redirects to Workday's outage page and its CXS API reports the site ID as
not found, so it's no longer a usable source. autodesk.com itself is
Akamai-blocked, even to headless Chromium.

It uses the same Eightfold `pcsx` search API as Microsoft (scrapers/microsoft.py):
`GET https://jobs.autodesk.com/api/pcsx/search?domain=autodesk.com&query=&location=Canada&start=N`,
10 per page, with no auth (just a browser User-Agent).

- `location=Canada` is a real filter: 16 of 62 jobs worldwide on 2026-09-25.
- Category: unlike Microsoft's tenant, `department` here holds payroll-ish
  values ("Non-Commission", "Canada - Time Tracking"), so it's useless for
  scoping. The page's "Job Category" smart filter is the real facet,
  passed as a repeatable `filter_job_category` param (confirmed via the
  response's `appliedFilters.jobCategory`). Scope: "development
  engineering", "artificial intelligence", "cybersecurity", "technology"
  (7 Canadian jobs).
  - Internships are filed under a catch-all "intern fg" category covering
    all functions, so software co-ops in Montréal aren't included.
- `postedTs` is 0 on this tenant, so the posted date comes from
  `creationTs` (a Unix timestamp).
- Fields: `displayJobId` (= Workday-style req ID like "26WD100437",
  external_id), `name`, `locations[]` (often a long list of regional
  "AMER - Canada - <province> - Remote" variants — Canadian ones are shown),
  `positionUrl` (prefix with the site origin).
"""

import logging
from datetime import datetime, timezone

import httpx

from .base import CANADA_PATTERN, NormalizedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://jobs.autodesk.com"
SEARCH_URL = f"{BASE_URL}/api/pcsx/search"
DOMAIN = "autodesk.com"
LOCATION_FILTER = "Canada"
JOB_CATEGORIES = ["development engineering", "artificial intelligence", "cybersecurity", "technology"]
CATEGORY_LABEL = "Development Engineering / Technology"
MAX_PAGES = 50
MAX_LOCATIONS_SHOWN = 3
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "application/json",
}


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    start = 0

    with httpx.Client(timeout=30, headers=HEADERS) as client:
        for _ in range(MAX_PAGES):
            params = [("domain", DOMAIN), ("query", ""), ("location", LOCATION_FILTER), ("start", str(start))]
            params += [("filter_job_category", category) for category in JOB_CATEGORIES]
            response = client.get(SEARCH_URL, params=params)
            response.raise_for_status()
            postings = (response.json().get("data") or {}).get("positions") or []
            if not postings:
                break
            new_on_page = 0
            for raw in postings:
                job_id = raw.get("displayJobId") or str(raw["id"])
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                new_on_page += 1
                jobs.append(_normalize(job_id, raw))
            if new_on_page == 0:
                break
            start += len(postings)
        else:
            logger.warning("Autodesk scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Autodesk: fetched %d Canada + tech-category jobs", len(jobs))
    return jobs


def _normalize(job_id: str, raw: dict) -> NormalizedJob:
    locations = raw.get("locations") or []
    canadian = [loc for loc in locations if CANADA_PATTERN.search(loc)] or locations
    location = "; ".join(canadian[:MAX_LOCATIONS_SHOWN])
    if len(canadian) > MAX_LOCATIONS_SHOWN:
        location += f" (+{len(canadian) - MAX_LOCATIONS_SHOWN} more)"

    timestamp = raw.get("postedTs") or raw.get("creationTs")
    posted_date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d") if timestamp else None
    return {
        "external_id": job_id,
        "title": raw["name"].strip(),
        "url": f"{BASE_URL}{raw['positionUrl']}" if raw.get("positionUrl") else f"{BASE_URL}/careers/job/{raw['id']}",
        "location": location,
        "category": CATEGORY_LABEL,
        "posted_date": posted_date,
        "platform": "Eightfold",
    }
