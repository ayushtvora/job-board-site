"""Manulife careers scraper, scoped to Canada + Information Technology.

Scrapes Manulife's **Workday tenant directly**, not the public careers site
at careers.manulife.com. That site is a Phenom People front-end (same
platform as RBC/BMO), but it sits behind an Akamai WAF that returns an
immediate 403 to every automated client tried — plain HTTP, browser-like
headers, and a real headless Chromium, from several different networks
including the server this scraper runs on. It's an instant block page, not
a JS challenge, so there's nothing for a scraper to solve. See CLAUDE.md's
"Manulife scraping approach" section.

Workday is the system of record behind that front-end (as it is for RBC and
BMO, whose apply links also point at Workday), and its API is not behind the
WAF, so it's used as the source instead. Approach is otherwise identical to
the other Workday scrapers — see scrapers/soti.py's docstring.

Manulife-specific notes:

- Tenant/site: `manulife.wd3.myworkdayjobs.com/MFCJH_Jobs` (a combined
  Manulife/John Hancock careers site). The site ID isn't guessable; it was
  found from a real apply link to this tenant published on a job aggregator.
- Facet parameters are `jobFamilyGroup` (Job Category) and
  `Location_Country`, confirmed against the site's own facet metadata:
  `838ae04677e543c2a0a85dfd1cab030a` = "Information Technology Group",
  `a30a87ed25634629aa6c3958aa2b91ea` = "Canada" (the same shared Canada ID
  used by SOTI/CIBC/TD).
- `bulletFields` is `[reqId, city]` here — the second element is a location,
  not a category like TD's job family — so `category` is hardcoded to the
  filtered facet's label.
- **Location comes from the detail endpoint, not the listing.** Manulife has
  many multi-location postings, for which the listing's `locationsText` is a
  useless placeholder like "2 Locations" / "50 Locations". The detail
  endpoint's `jobPostingInfo.location` is always a real place name.
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

TENANT = "manulife"
SITE = "MFCJH_Jobs"
BASE_URL = "https://manulife.wd3.myworkdayjobs.com"
LIST_URL = f"{BASE_URL}/wday/cxs/{TENANT}/{SITE}/jobs"
DETAIL_URL_TEMPLATE = f"{BASE_URL}/wday/cxs/{TENANT}/{SITE}{{path}}"

# Opaque Workday facet IDs, not derivable from their labels — confirmed
# against the site's own facet metadata (see module docstring).
CATEGORY_FACET_ID = "838ae04677e543c2a0a85dfd1cab030a"  # Information Technology Group
COUNTRY_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"  # Canada
CATEGORY_LABEL = "Information Technology Group"

PAGE_SIZE = 20
MAX_PAGES = 50  # safety cap; this filter currently has ~33 jobs


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
                        "Location_Country": [COUNTRY_FACET_ID],
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
            logger.warning("Manulife scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Manulife: fetched %d jobs (site reported total=%s)", len(jobs), total)
    return jobs


def _normalize(client: httpx.Client, job_id: str, raw: dict) -> NormalizedJob:
    detail = _fetch_detail(client, raw["externalPath"])
    return {
        "external_id": job_id,
        "title": raw["title"],
        "url": detail["externalUrl"],
        "location": detail.get("location") or raw["locationsText"],
        "category": CATEGORY_LABEL,
        "posted_date": detail.get("startDate"),
        "platform": "Workday",
    }


def _fetch_detail(client: httpx.Client, external_path: str) -> dict:
    response = client.get(DETAIL_URL_TEMPLATE.format(path=external_path))
    response.raise_for_status()
    return response.json()["jobPostingInfo"]
