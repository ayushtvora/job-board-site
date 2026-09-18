"""CIBC careers scraper, scoped to Canada + Information Technology.

Same Workday CXS API approach as SOTI (scrapers/soti.py) — see that module's
docstring for how this pattern works in general. CIBC-specific notes:

- Tenant/site: `cibc.wd3.myworkdayjobs.com/search` (the "site" segment is
  `search`, not `Careers` as in SOTI's case — this varies per tenant and is
  just read off the site's own URL).
- Facet parameter names are `jobFamilyGroup` (Job Category) and `Country`,
  confirmed against the site's own facet metadata: `jobFamilyGroup`
  value `4bbe6c74e8a70126f29430a881012510` = "Information Technology",
  `Country` value `a30a87ed25634629aa6c3958aa2b91ea` = "Canada" — the same
  opaque Canada ID SOTI's job detail responses used, suggesting Workday
  reuses common reference IDs (like countries) across tenants.
- Unlike SOTI, `bulletFields` here is just `[reqId]` — no second field with
  a more specific category — so `category` is hardcoded to the filtered
  facet's label, same reasoning as SOTI's category.
- Posted date and canonical apply URL: same as SOTI, from each job's detail
  endpoint (`jobPostingInfo.startDate` / `.externalUrl`).
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

TENANT = "cibc"
SITE = "search"
BASE_URL = "https://cibc.wd3.myworkdayjobs.com"
LIST_URL = f"{BASE_URL}/wday/cxs/{TENANT}/{SITE}/jobs"
DETAIL_URL_TEMPLATE = f"{BASE_URL}/wday/cxs/{TENANT}/{SITE}{{path}}"

# Opaque Workday facet IDs, not derivable from their labels — confirmed
# against the site's own facet metadata (see module docstring).
CATEGORY_FACET_ID = "4bbe6c74e8a70126f29430a881012510"  # Information Technology
COUNTRY_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"  # Canada
CATEGORY_LABEL = "Information Technology"

PAGE_SIZE = 20
MAX_PAGES = 50  # safety cap; this filter currently has ~31 jobs


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
                        "jobFamilyGroup": [CATEGORY_FACET_ID],
                        "Country": [COUNTRY_FACET_ID],
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
            logger.warning("CIBC scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("CIBC: fetched %d jobs (site reported total=%s)", len(jobs), total)
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
