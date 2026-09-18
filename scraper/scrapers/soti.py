"""SOTI careers scraper, scoped to Mississauga HQ + Product Development.

SOTI's careers site runs on Workday directly (unlike RBC's Phenom People
site), which exposes a documented CXS JSON API — no HTML scraping needed.
See CLAUDE.md's "SOTI scraping approach" section for how this was found.

- List endpoint (POST .../wday/cxs/soti/Careers/jobs) takes an `appliedFacets`
  dict keyed by Workday facet parameter names; the values are the same
  opaque facet IDs that appear as query params on the site's own filtered
  URLs (e.g. `locations=<id>`).
- The list endpoint does not return a category, or an exact posted date, per
  job — only a relative string like "Posted 18 Days Ago". Since this scraper
  filters to one fixed category facet, every job it returns is by definition
  that category, so `category` is hardcoded to its label rather than read
  per-job.
- For an exact `posted_date` (and the canonical apply URL), each job's
  detail endpoint (GET .../wday/cxs/soti/Careers<externalPath>) is fetched;
  its `jobPostingInfo.startDate` is a plain ISO date — confirmed this
  matches the list's relative "Posted N Days Ago" text exactly (e.g. 18
  days before the date this was checked).
- `bulletFields[0]` in the list response is the job requisition ID (e.g.
  "R09972") and matches the detail endpoint's `jobReqId` — used as
  `external_id`.
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

TENANT = "soti"
SITE = "Careers"
BASE_URL = "https://soti.wd3.myworkdayjobs.com"
LIST_URL = f"{BASE_URL}/wday/cxs/{TENANT}/{SITE}/jobs"
DETAIL_URL_TEMPLATE = f"{BASE_URL}/wday/cxs/{TENANT}/{SITE}{{path}}"

# Opaque Workday facet IDs, not derivable from their labels — confirmed
# against the site's own facet metadata (see module docstring).
LOCATION_FACET_ID = "023f9d25c4c11000bbfc52f5b4120000"  # Mississauga, Canada – Meadowvale Office (HQ)
CATEGORY_FACET_ID = "267bdbcbbd671001697698c0843a0001"  # Product Development
CATEGORY_LABEL = "Product Development"

PAGE_SIZE = 20
MAX_PAGES = 50  # safety cap; this category currently has ~12 jobs


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    offset = 0
    total: int | None = None

    with httpx.Client(timeout=30) as client:
        for _ in range(MAX_PAGES):
            response = client.post(
                LIST_URL,
                json={
                    "appliedFacets": {
                        "locations": [LOCATION_FACET_ID],
                        "EEB_-_Job_Categories_for_External_Site_Extended": [CATEGORY_FACET_ID],
                    },
                    "limit": PAGE_SIZE,
                    "offset": offset,
                    "searchText": "",
                },
            )
            response.raise_for_status()
            payload = response.json()
            # Only trust `total` from the first page — confirmed some Workday
            # tenants (e.g. TD) report it as 0 on later pages, which would
            # otherwise make `offset >= total` trip early and truncate results.
            if total is None:
                total = payload["total"]
            postings = payload["jobPostings"]
            if not postings:
                break

            for raw in postings:
                job_id = raw["bulletFields"][0]
                # Mirrors RBC's dedupe: not strictly known to be needed here,
                # but cheap insurance against overlap under the default sort.
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                jobs.append(_normalize(client, job_id, raw))

            offset += PAGE_SIZE
            if offset >= total:
                break
        else:
            logger.warning("SOTI scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("SOTI: fetched %d jobs (site reported total=%s)", len(jobs), total)
    return jobs


def _normalize(client: httpx.Client, job_id: str, raw: dict) -> NormalizedJob:
    detail = _fetch_detail(client, raw["externalPath"])
    return {
        "external_id": job_id,
        "title": raw["title"],
        "url": detail["externalUrl"],
        "location": raw["locationsText"],
        "category": CATEGORY_LABEL,
        "posted_date": detail.get("startDate"),
        "platform": "Workday",
    }


def _fetch_detail(client: httpx.Client, external_path: str) -> dict:
    response = client.get(DETAIL_URL_TEMPLATE.format(path=external_path))
    response.raise_for_status()
    return response.json()["jobPostingInfo"]
