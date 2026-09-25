"""Oracle (the corporation) careers scraper — Product and Research jobs.

Oracle's own careers site (careers.oracle.com) runs on Oracle Recruiting
Cloud (Fusion Cloud HCM), not a third-party ATS. It exposes a public,
unauthenticated REST API (found via the CSP header on the marketing page)
— no browser/session needed, plain HTTP GETs are enough. See CLAUDE.md's
"Intel, Oracle, Spotify, Adobe, Sony, AMD, Uber scraping approach" section
(Oracle bullet) for how this was found.

- Category filter: `selectedCategoriesFacet=<id>` — "Product and Research"
  = 302958497961752 (confirmed: narrows a global ~758-total unfiltered
  count to this category's own count).
- Canada filtering is fuzzy, not exact: confirmed the Canada location facet
  (`selectedLocationsFacet=300000000106749`) applied *together* with the
  category facet returns a small candidate set, but some entries have
  `PrimaryLocation` like "United States" (a real data quirk on Oracle's own
  site, not a bug here) — so the candidate set is filtered again
  client-side on `PrimaryLocation` containing "Canada".
- `JobFamily`/`JobFunction` are null at this site number (`CX_1`) — not
  used.
- The response shape is `{"items": [{... "requisitionList": [...],
  "TotalJobsCount": N, ...}], ...}` — one search-result object per call,
  confirmed live; `TotalJobsCount` reflects only the first page's query, so
  (per the existing TD-bug-fix convention used elsewhere in this scraper
  suite) it's only trusted from the first page.
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://eeho.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
SITE_NUMBER = "CX_1"
CATEGORY_LABEL = "Product and Research"
CATEGORY_FACET_ID = "302958497961752"  # "Product and Research"
LOCATION_FACET_ID = "300000000106749"  # "Canada" (fuzzy — see module docstring)

PAGE_SIZE = 20
MAX_PAGES = 20  # safety cap; this candidate set is currently in the single digits


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    offset = 0
    total: int | None = None

    with httpx.Client(timeout=30) as client:
        for _ in range(MAX_PAGES):
            finder = (
                f"findReqs;siteNumber={SITE_NUMBER},"
                "facetsList=LOCATIONS;CATEGORIES,"
                f"selectedCategoriesFacet={CATEGORY_FACET_ID},"
                f"selectedLocationsFacet={LOCATION_FACET_ID},"
                f"limit={PAGE_SIZE},offset={offset}"
            )
            response = client.get(
                BASE_URL,
                params={
                    "onlyData": "true",
                    "expand": "requisitionList",
                    "finder": finder,
                },
            )
            response.raise_for_status()
            item = response.json()["items"][0]

            # Only trust `total` from the first page — same convention as
            # the Workday scrapers' TD-bug fix (some tenants/APIs report a
            # stale or zeroed-out total on later pages).
            if total is None:
                total = item.get("TotalJobsCount", 0)
            requisitions = item.get("requisitionList") or []
            if not requisitions:
                break

            for raw in requisitions:
                job_id = str(raw["Id"])
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                primary_location = raw.get("PrimaryLocation") or ""
                if "canada" not in primary_location.lower():
                    # Part of Oracle's fuzzy location-facet match, not
                    # actually Canada — see module docstring.
                    continue
                jobs.append(_normalize(raw))

            offset += PAGE_SIZE
            if offset >= total:
                break
        else:
            logger.warning("Oracle scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info(
        "Oracle: fetched %d Canada jobs (site reported candidate total=%s before client-side location filter)",
        len(jobs),
        total,
    )
    return jobs


def _normalize(raw: dict) -> NormalizedJob:
    return {
        "external_id": str(raw["Id"]),
        "title": raw["Title"],
        "url": f"https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/{SITE_NUMBER}/job/{raw['Id']}",
        "location": raw.get("PrimaryLocation", ""),
        "category": CATEGORY_LABEL,
        "posted_date": raw.get("PostedDate"),
        "platform": "Oracle Recruiting Cloud",
    }
