"""Intel careers scraper, scoped to Canada + Software Engineering.

Same Workday CXS API approach as SOTI (scrapers/soti.py) — see that module's
docstring for how this pattern works in general. Intel-specific notes:

- The marketing-facing `jobs.intel.com` domain is dead (redirect loop); the
  real backend is Workday, tenant `intel.wd1.myworkdayjobs.com/External`.
- Category facet is `jobFamilyGroup`, value
  `ace7a3d23b7e01a0544279031a0ec85c` = "Software Engineering".
- **No single country-level facet exists** — locations are city-granular,
  nested as a `locations` facet under a `locationMainGroup` facet group in
  the site's facet metadata (confirmed by walking the metadata tree; the
  `appliedFacets` key to actually submit is the nested facet's own
  parameter name, `locations`, same as how TD's `locationCountry` is nested
  under `locationMainGroup` in its metadata but still submitted as a flat
  top-level key). Canada requires passing **both** `"Canada, Toronto"`
  (`1e4a4eb3adf1019f4237e975bf81b3ce`) and `"Virtual Canada"`
  (`3d7e019f2bb20100b6accdbea05c0000`) in that one list — confirmed
  Toronto-only gives 0 results, both together gives 3 (all "Virtual
  Canada"), matching this combined category+location filter exactly.
- `bulletFields` is single-element (`[reqId]`) for jobs matching this
  filter — `category` is hardcoded to the filtered facet's label, same
  reasoning as SOTI. (Note: some *other* Intel postings outside this filter
  have been seen with a non-ID first bulletField like "Spotlight Job", but
  none of the 3 real matches for this filter do — `bulletFields[0]` is safe
  here.)
- Posted date and canonical apply URL: same as SOTI, from each job's detail
  endpoint (`jobPostingInfo.startDate` / `.externalUrl`).
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

TENANT = "intel"
SITE = "External"
BASE_URL = "https://intel.wd1.myworkdayjobs.com"
LIST_URL = f"{BASE_URL}/wday/cxs/{TENANT}/{SITE}/jobs"
DETAIL_URL_TEMPLATE = f"{BASE_URL}/wday/cxs/{TENANT}/{SITE}{{path}}"

# Opaque Workday facet IDs, not derivable from their labels — confirmed
# against the site's own facet metadata (see module docstring).
CATEGORY_FACET_ID = "ace7a3d23b7e01a0544279031a0ec85c"  # Software Engineering
LOCATION_FACET_IDS = [
    "1e4a4eb3adf1019f4237e975bf81b3ce",  # Canada, Toronto
    "3d7e019f2bb20100b6accdbea05c0000",  # Virtual Canada
]
CATEGORY_LABEL = "Software Engineering"

PAGE_SIZE = 20
MAX_PAGES = 50  # safety cap; this filter currently has ~3 jobs


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
                        "locations": LOCATION_FACET_IDS,
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
            logger.warning("Intel scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Intel: fetched %d jobs (site reported total=%s)", len(jobs), total)
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
