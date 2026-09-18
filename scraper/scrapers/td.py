"""TD careers scraper, scoped to Canada + Technology Solutions.

Same Workday CXS API approach as SOTI (scrapers/soti.py) — see that module's
docstring for how this pattern works in general. TD-specific notes:

- Tenant/site: `td.wd3.myworkdayjobs.com/TD_Bank_Careers`.
- Facet parameter names are `jobFamilyGroup` (Job Category) and
  `locationCountry` (nested under a `locationMainGroup` facet group in the
  site's facet metadata), confirmed: `jobFamilyGroup` value
  `de769652963501f2001247b507040dac` = "Technology Solutions",
  `locationCountry` value `a30a87ed25634629aa6c3958aa2b91ea` = "Canada" —
  the same opaque Canada ID seen on SOTI and CIBC.
- Unlike SOTI/CIBC, `bulletFields` here is `[reqId, jobFamily]` — TD's
  career site is configured to show a second, more specific field per job:
  its "Job Family" (a finer-grained sub-category under "Job Category", e.g.
  "Engineering", "Business Systems Analysis" — confirmed these values exist
  in the site's own `jobFamily` facet). Used as `category` directly instead
  of hardcoding the coarser "Technology Solutions" filter label, since it's
  real per-job data from the source.
- Posted date and canonical apply URL: same as SOTI, from each job's detail
  endpoint (`jobPostingInfo.startDate` / `.externalUrl`).
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

TENANT = "td"
SITE = "TD_Bank_Careers"
BASE_URL = "https://td.wd3.myworkdayjobs.com"
LIST_URL = f"{BASE_URL}/wday/cxs/{TENANT}/{SITE}/jobs"
DETAIL_URL_TEMPLATE = f"{BASE_URL}/wday/cxs/{TENANT}/{SITE}{{path}}"

# Opaque Workday facet IDs, not derivable from their labels — confirmed
# against the site's own facet metadata (see module docstring).
CATEGORY_FACET_ID = "de769652963501f2001247b507040dac"  # Technology Solutions
COUNTRY_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"  # Canada
FALLBACK_CATEGORY_LABEL = "Technology Solutions"

PAGE_SIZE = 20
MAX_PAGES = 50  # safety cap; this filter currently has ~95 jobs


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
                        "locationCountry": [COUNTRY_FACET_ID],
                    },
                    "limit": PAGE_SIZE,
                    "offset": offset,
                    "searchText": "",
                },
            )
            response.raise_for_status()
            payload = response.json()
            # Only trust `total` from the first page — confirmed TD's own API
            # reports it as 0 on later pages, which would otherwise make
            # `offset >= total` trip early and truncate results.
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
            logger.warning("TD scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("TD: fetched %d jobs (site reported total=%s)", len(jobs), total)
    return jobs


def _normalize(client: httpx.Client, job_id: str, raw: dict) -> NormalizedJob:
    detail = _fetch_detail(client, raw["externalPath"])
    bullet_fields = raw.get("bulletFields") or []
    category = bullet_fields[1] if len(bullet_fields) > 1 else FALLBACK_CATEGORY_LABEL
    return {
        "external_id": job_id,
        "title": raw["title"],
        "url": detail["externalUrl"],
        "location": raw["locationsText"],
        "category": category,
        "posted_date": detail.get("startDate"),
        "platform": "Workday",
    }


def _fetch_detail(client: httpx.Client, external_path: str) -> dict:
    response = client.get(DETAIL_URL_TEMPLATE.format(path=external_path))
    response.raise_for_status()
    return response.json()["jobPostingInfo"]
