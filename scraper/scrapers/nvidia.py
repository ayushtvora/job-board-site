"""Nvidia careers scraper, scoped to Canada + Engineering.

Same Workday CXS API approach as SOTI (scrapers/soti.py) — see that module's
docstring for how this pattern works in general. Nvidia-specific notes:

- Tenant/site: `nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite`.
- Category facet is `jobFamilyGroup`, value `0c40f6bd1d8f10ae43ffaefd46dc7e78`
  = "Engineering".
- **Country is not a flat facet here** (unlike SOTI/CIBC/TD/Manulife's
  `Country`/`Location_Country`) — it's nested under a `locationHierarchy1`
  facet (itself under a `locationMainGroup` facet group in the site's own
  facet metadata), value `2fcb99c455831013ea529c3b93ba3236` = "Canada" — a
  tenant-specific ID, *not* the shared `a30a87ed25634629aa6c3958aa2b91ea`
  used elsewhere, confirming each tenant's facet IDs need independent
  verification even when the facet *parameter name* (`locationCountry`
  Sony/SOTI/CIBC/TD vs. `locationHierarchy1` here) differs too.
- Combined `appliedFacets: {"jobFamilyGroup": [...], "locationHierarchy1": [...]}`
  confirmed working: 10 real Canada + Engineering jobs.
- `bulletFields` is single-element here (`[reqId]`, no second field like
  TD/Manulife) — so `category` is hardcoded to the filtered facet's label.
- Posted date and canonical apply URL: same as SOTI, from each job's detail
  endpoint (`jobPostingInfo.startDate` / `.externalUrl`).
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

TENANT = "nvidia"
SITE = "NVIDIAExternalCareerSite"
BASE_URL = "https://nvidia.wd5.myworkdayjobs.com"
LIST_URL = f"{BASE_URL}/wday/cxs/{TENANT}/{SITE}/jobs"
DETAIL_URL_TEMPLATE = f"{BASE_URL}/wday/cxs/{TENANT}/{SITE}{{path}}"

# Opaque Workday facet IDs, not derivable from their labels — confirmed
# against the site's own facet metadata (see module docstring).
CATEGORY_FACET_ID = "0c40f6bd1d8f10ae43ffaefd46dc7e78"  # Engineering
COUNTRY_FACET_ID = "2fcb99c455831013ea529c3b93ba3236"  # Canada (tenant-specific, not the shared cross-tenant ID)
CATEGORY_LABEL = "Engineering"

PAGE_SIZE = 20
MAX_PAGES = 50  # safety cap; this filter currently has ~10 jobs


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
                        "locationHierarchy1": [COUNTRY_FACET_ID],
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
            logger.warning("Nvidia scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Nvidia: fetched %d jobs (site reported total=%s)", len(jobs), total)
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
