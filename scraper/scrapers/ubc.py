"""UBC careers scraper, scoped to M&P Information Systems & Tech staff jobs.

Same Workday CXS API approach as SOTI (scrapers/soti.py) — see that module's
docstring for how this pattern works in general. UBC-specific notes:

- UBC runs three separate Workday sites by employee type; staff jobs are the
  relevant one here. Tenant/site: `ubc.wd10.myworkdayjobs.com/ubcstaffjobs`.
- **No country filter is applied or needed** — every location facet value on
  this site is already a BC campus (Vancouver/Okanagan), so there's nothing
  to narrow to Canada.
- Category facet here is `jobFamily` (not `jobFamilyGroup` like the other
  Workday tenants in this project) — a finer-grained, union/role-based
  facet on this site. Closest Software-Engineering equivalent, confirmed
  against actual returned job titles ("Programmer Systems Analyst II",
  "Support Analyst I", "Network Analyst I, Wireless"):
  `"M&P Information Systems & Tech"` = `0f50d6e300ee011d7120b51e4001a9f9`.
- `bulletFields` is single-element here (`[reqId]`) — `category` is
  hardcoded to the filtered facet's label, same reasoning as SOTI.
- Posted date and canonical apply URL: same as SOTI, from each job's detail
  endpoint (`jobPostingInfo.startDate` / `.externalUrl`).
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

TENANT = "ubc"
SITE = "ubcstaffjobs"
BASE_URL = "https://ubc.wd10.myworkdayjobs.com"
LIST_URL = f"{BASE_URL}/wday/cxs/{TENANT}/{SITE}/jobs"
DETAIL_URL_TEMPLATE = f"{BASE_URL}/wday/cxs/{TENANT}/{SITE}{{path}}"

# Opaque Workday facet ID, not derivable from its label — confirmed against
# the site's own facet metadata (see module docstring).
CATEGORY_FACET_ID = "0f50d6e300ee011d7120b51e4001a9f9"  # M&P Information Systems & Tech
CATEGORY_LABEL = "M&P Information Systems & Tech"

PAGE_SIZE = 20
MAX_PAGES = 50  # safety cap; this filter currently has ~4 jobs


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
                        "jobFamily": [CATEGORY_FACET_ID],
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
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                jobs.append(_normalize(client, job_id, raw))

            offset += PAGE_SIZE
            if offset >= total:
                break
        else:
            logger.warning("UBC scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("UBC: fetched %d jobs (site reported total=%s)", len(jobs), total)
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
