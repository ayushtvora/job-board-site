"""Shared helper for Workday CXS-API scrapers.

Same approach as SOTI (scrapers/soti.py — see its docstring for how the
CXS API was found): POST the list endpoint with `appliedFacets`, paginate by
`limit`/`offset`, then GET each job's detail endpoint for the real
`startDate`, canonical `externalUrl`, and a real place name for `location`.

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
- Postings without an `externalPath` are skipped. CIBC's list response
  has been seen to include a stub posting with only `bulletFields`
  (confirmed 2026-09-25), which has no detail endpoint to fetch.
"""

import logging
from collections.abc import Callable

import httpx

from .base import CANADA_PATTERN, NormalizedJob

logger = logging.getLogger(__name__)

PAGE_SIZE = 20


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
    client-side, for filters the tenant's facets can't express.
    `category_fn(list_item, detail)` can read a real per-job category (e.g.
    TD's job family in `bulletFields`); `category_label` is the fallback."""
    list_url = f"{base_url}/wday/cxs/{tenant}/{site}/jobs"
    detail_url = f"{base_url}/wday/cxs/{tenant}/{site}{{path}}"

    jobs: list[NormalizedJob] = []
    seen_paths: set[str] = set()
    offset = 0
    total: int | None = None

    with httpx.Client(timeout=30) as client:
        for _ in range(max_pages):
            response = client.post(
                list_url,
                json={"appliedFacets": applied_facets, "limit": PAGE_SIZE, "offset": offset, "searchText": ""},
            )
            response.raise_for_status()
            payload = response.json()
            if total is None:
                total = payload["total"]
            postings = payload["jobPostings"]
            if not postings:
                break

            for raw in postings:
                path = raw.get("externalPath")
                if path is None:
                    logger.warning("%s: skipping posting with no externalPath: %s", name, raw)
                    continue
                if path in seen_paths:
                    continue
                seen_paths.add(path)
                detail_response = client.get(detail_url.format(path=path))
                detail_response.raise_for_status()
                detail = detail_response.json()["jobPostingInfo"]
                if job_filter is not None and not job_filter(raw, detail):
                    continue
                category = (category_fn(raw, detail) if category_fn else None) or category_label
                jobs.append(_normalize(raw, detail, category))

            offset += PAGE_SIZE
            if offset >= total:
                break
        else:
            logger.warning("%s scrape hit max_pages=%d without finishing — got %d jobs", name, max_pages, len(jobs))

    logger.info("%s: fetched %d jobs (site reported total=%s)", name, len(jobs), total)
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
