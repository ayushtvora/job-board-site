"""Shared helper for Oracle Recruiting Cloud (Fusion Cloud HCM) scrapers.

Same API as Oracle and Metrolinx (see CLAUDE.md's "Oracle scraping
approach" / "Metrolinx scraping approach"): each tenant exposes a public,
unauthenticated REST resource,

    GET https://<pod host>/hcmRestApi/resources/latest/recruitingCEJobRequisitions
        ?onlyData=true&expand=<expand>
        &finder=findReqs;siteNumber=<site>,facetsList=<facets>,<filters>,limit=N,offset=N[,sortBy=...]

- Everything that filters or pages goes inside the single `finder` param,
  as comma-separated `key=value` pairs (`selectedCategoriesFacet=<id>`,
  `selectedLocationsFacet=<id>`, `limit`, `offset`, `sortBy`). Facet IDs
  come from the response's own `categoriesFacet`/`locationsFacet` arrays.
- `expand` must include `requisitionList` — without it the response has
  facets but no jobs. Some tenants (Metrolinx) only return the list when
  it's the fuller `requisitionList.secondaryLocations,flexFieldsFacet.values`.
- The response is `{"items": [{"TotalJobsCount": N, "requisitionList": [...]}]}`.
  `total` is only trusted from the first page (same convention as Workday).
- Per job: `Id` (stable numeric, used as `external_id`), `Title`,
  `PostedDate` (already a plain ISO date), `PrimaryLocation`.
  `JobFamily`/`JobFunction` are null in practice, so the category is either
  the filtered facet's label or `category_fn`'s result.
- Data roles: tenants filtered by `selectedCategoriesFacet` get a second
  search without it, `keyword=<term>` for each of `DATA_SEARCH_TERMS`,
  keeping only data titles (sorted by relevance, so paging stops at the
  first page without one).
- The public job page is `https://<host>/hcmUI/CandidateExperience/en/sites/<site>/job/<Id>`.
"""

import logging
from collections.abc import Callable

import httpx

from .base import DATA_SEARCH_TERMS, NormalizedJob, is_data_title

logger = logging.getLogger(__name__)

MAX_PAGES = 20
DATA_SEARCH_CATEGORY = "Data (keyword search)"


def scrape_oracle_recruiting(
    *,
    name: str,
    host: str,
    site_number: str = "CX_1",
    facets_list: str = "LOCATIONS;CATEGORIES",
    expand: str = "requisitionList",
    finder_filters: dict[str, str] | None = None,
    sort_by: str | None = None,
    page_size: int = 25,
    category_label: str = "",
    category_fn: Callable[[dict], str] | None = None,
    job_filter: Callable[[dict], bool] | None = None,
) -> list[NormalizedJob]:
    """`finder_filters` are extra `findReqs` pairs, e.g.
    `{"selectedCategoriesFacet": "<id>"}`. `job_filter(raw)` can drop jobs
    client-side, including data-search ones; `category_fn(raw)` overrides
    `category_label`."""
    api_url = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    job_url = f"https://{host}/hcmUI/CandidateExperience/en/sites/{site_number}/job/{{id}}"

    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()

    with httpx.Client(timeout=30) as client:

        def scrape_pass(filters: dict[str, str], data_only: bool) -> int | None:
            """One paged search. With `data_only` (a keyword search, sorted
            by relevance), only data titles are kept, and paging stops at
            the first page without one."""
            offset = 0
            total: int | None = None
            for _ in range(MAX_PAGES):
                pairs = {
                    "siteNumber": site_number,
                    "facetsList": facets_list,
                    **filters,
                    "limit": str(page_size),
                    "offset": str(offset),
                }
                if sort_by and not data_only:
                    pairs["sortBy"] = sort_by
                finder = "findReqs;" + ",".join(f"{key}={value}" for key, value in pairs.items())
                response = client.get(api_url, params={"onlyData": "true", "expand": expand, "finder": finder})
                response.raise_for_status()
                item = response.json()["items"][0]
                if total is None:
                    total = item.get("TotalJobsCount", 0)
                requisitions = item.get("requisitionList") or []
                if not requisitions:
                    break

                for raw in requisitions:
                    job_id = str(raw["Id"])
                    if job_id in seen_ids or (data_only and not is_data_title(raw["Title"])):
                        continue
                    seen_ids.add(job_id)
                    if job_filter is not None and not job_filter(raw):
                        continue
                    jobs.append({
                        "external_id": job_id,
                        "title": raw["Title"].strip(),
                        "url": job_url.format(id=job_id),
                        "location": raw.get("PrimaryLocation") or "",
                        "category": DATA_SEARCH_CATEGORY if data_only else (category_fn(raw) if category_fn else category_label),
                        "posted_date": raw.get("PostedDate"),
                        "platform": "Oracle Recruiting Cloud",
                    })

                offset += page_size
                if offset >= total or (data_only and not any(is_data_title(raw["Title"]) for raw in requisitions)):
                    break
            else:
                logger.warning("%s scrape hit MAX_PAGES=%d without finishing — got %d jobs", name, MAX_PAGES, len(jobs))
            return total

        total = scrape_pass(finder_filters or {}, data_only=False)
        # Data roles outside the category facet, by keyword. Without a
        # category facet the first pass already saw every job.
        location_filters = {k: v for k, v in (finder_filters or {}).items() if k != "selectedCategoriesFacet"}
        if location_filters != (finder_filters or {}):
            for term in DATA_SEARCH_TERMS:
                scrape_pass({**location_filters, "keyword": term}, data_only=True)

    logger.info("%s: fetched %d jobs (site reported total=%s before client-side filters)", name, len(jobs), total)
    return jobs
