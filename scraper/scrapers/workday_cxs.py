"""Shared helper for Workday CXS-API scrapers.

Same approach as SOTI (scrapers/soti.py — see its docstring for how the
CXS API was found): POST the list endpoint with `appliedFacets`, paginate by
`limit`/`offset`, then GET each job's detail endpoint for the real
`startDate`, canonical `externalUrl`, and a real place name for `location`.
Each page's detail requests run a few at a time.

Per-tenant differences this absorbs, so each company module stays a small
config + its own investigation notes:

- `total` is only trusted from the first page (TD reports 0 on later pages).
- `external_id` comes from the detail endpoint's `jobReqId`, since the req
  ID's position in `bulletFields` varies by tenant (first for most, *last*
  for Thomson Reuters). Dedupe during pagination uses `externalPath`.
- `location` comes from the detail endpoint, since many tenants show a
  "3 Locations" placeholder in the list's `locationsText`. A country facet
  matches a posting if *any* of its locations is in that country, and the
  primary `location` is often a US city (e.g. Thomson Reuters postings
  that list Toronto as one of five `additionalLocations`), so Canadian
  locations are shown first, with a count of the rest.
- Data roles: after the configured search, the same search runs again
  without the category facets (`CATEGORY_FACET_KEYS`) for each of
  `DATA_SEARCH_TERMS`, keeping only data titles (before fetching any
  detail page). `searchText` also matches descriptions, but results are
  sorted by relevance with title matches first, so paging stops at the
  first page with no data title.
- Postings without an `externalPath` are skipped. CIBC's list response
  has been seen to include a stub posting with only `bulletFields`
  (confirmed 2026-09-25), which has no detail endpoint to fetch.
"""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import httpx

from .base import CANADA_PATTERN, DATA_SEARCH_TERMS, NormalizedJob, is_data_title

logger = logging.getLogger(__name__)

PAGE_SIZE = 20
# Detail pages fetched at once per tenant (one extra request per posting).
DETAIL_WORKERS = 4
# Facet parameters that pick a job category rather than a location, across
# the configured tenants. The data search drops these.
CATEGORY_FACET_KEYS = {
    "jobFamilyGroup",
    "jobFamily",
    "Functional_Area",
    "JobAreas",
    "EEB_-_Job_Categories_for_External_Site_Extended",
    "CF_Job_Posting_Anchor_Job_Category_EEB_Extended",
}
DATA_SEARCH_CATEGORY = "Data (keyword search)"


def scrape_workday(
    *,
    name: str,
    base_url: str,
    tenant: str,
    site: str,
    applied_facets: dict[str, list[str]],
    category_label: str,
    job_filter: Callable[[dict, dict], bool] | None = None,
    category_fn: Callable[[dict, dict], str | None] | None = None,
    max_pages: int = 50,
) -> list[NormalizedJob]:
    """Scrape one Workday site. `job_filter(list_item, detail)` can drop jobs
    client-side, for filters the tenant's facets can't express; it applies
    to the data search too. `category_fn(list_item, detail)` can read a real
    per-job category (e.g. TD's job family in `bulletFields`);
    `category_label` is the fallback."""
    list_url = f"{base_url}/wday/cxs/{tenant}/{site}/jobs"
    detail_url = f"{base_url}/wday/cxs/{tenant}/{site}{{path}}"

    jobs: list[NormalizedJob] = []
    seen_paths: set[str] = set()

    with httpx.Client(timeout=30) as client, ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as detail_pool:

        def fetch_detail(raw: dict) -> dict:
            detail_response = client.get(detail_url.format(path=raw["externalPath"]))
            detail_response.raise_for_status()
            return detail_response.json()["jobPostingInfo"]

        def scrape_pass(facets: dict[str, list[str]], search_text: str, data_only: bool) -> int | None:
            """One paged search. With `data_only`, only data titles are
            kept, and paging stops at the first page without one (results
            are sorted by relevance, so title matches come first)."""
            offset = 0
            total: int | None = None
            for _ in range(max_pages):
                response = client.post(
                    list_url,
                    json={"appliedFacets": facets, "limit": PAGE_SIZE, "offset": offset, "searchText": search_text},
                )
                response.raise_for_status()
                payload = response.json()
                if total is None:
                    total = payload["total"]
                postings = payload["jobPostings"]
                if not postings:
                    break

                new_postings = []
                for raw in postings:
                    path = raw.get("externalPath")
                    if path is None:
                        logger.warning("%s: skipping posting with no externalPath: %s", name, raw)
                        continue
                    if path in seen_paths or (data_only and not is_data_title(raw["title"])):
                        continue
                    seen_paths.add(path)
                    new_postings.append(raw)

                # map() re-raises the first failed fetch, so a failure still fails
                # the whole scrape rather than returning a partial job list.
                details = list(detail_pool.map(fetch_detail, new_postings))
                for raw, detail in zip(new_postings, details):
                    if job_filter is not None and not job_filter(raw, detail):
                        continue
                    category = (category_fn(raw, detail) if category_fn else None) or (
                        DATA_SEARCH_CATEGORY if data_only else category_label
                    )
                    jobs.append(_normalize(raw, detail, category))

                offset += PAGE_SIZE
                if offset >= total or (data_only and not any(is_data_title(raw["title"]) for raw in postings)):
                    break
            else:
                logger.warning("%s scrape hit max_pages=%d without finishing — got %d jobs", name, max_pages, len(jobs))
            return total

        total = scrape_pass(applied_facets, "", data_only=False)
        # Data roles outside the category facets: the same search minus
        # those facets, by keyword. Tenants without a category facet
        # already got every job in the first pass.
        location_facets = {key: ids for key, ids in applied_facets.items() if key not in CATEGORY_FACET_KEYS}
        if location_facets != applied_facets:
            for term in DATA_SEARCH_TERMS:
                scrape_pass(location_facets, term, data_only=True)

    logger.info("%s: fetched %d jobs (site reported total=%s for the category facets)", name, len(jobs), total)
    return jobs


def _normalize(raw: dict, detail: dict, category: str) -> NormalizedJob:
    bullet_fields = raw.get("bulletFields") or []
    return {
        "external_id": detail.get("jobReqId") or (bullet_fields[0] if bullet_fields else raw["externalPath"]),
        "title": raw["title"],
        "url": detail.get("externalUrl") or "",
        "location": _location(raw, detail),
        "category": category,
        "posted_date": detail.get("startDate"),
        "platform": "Workday",
    }


def _location(raw: dict, detail: dict) -> str:
    primary = detail.get("location") or raw.get("locationsText") or ""
    all_locations = [primary, *(detail.get("additionalLocations") or [])]
    canadian = [loc for loc in all_locations if CANADA_PATTERN.search(loc)]
    if not canadian:
        return primary
    others = len(all_locations) - len(canadian)
    return "; ".join(canadian) + (f" (+{others} more)" if others else "")
