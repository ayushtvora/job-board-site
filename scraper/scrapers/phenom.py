"""Shared helper for Phenom People career-site scrapers.

Same `phApp.ddo` blob approach as RBC/BMO (scrapers/rbc.py, scrapers/bmo.py
— see CLAUDE.md's "RBC scraping approach"): each search-results page embeds
its job list as JSON at `phApp.ddo.eagerLoadRefineSearch.data.jobs`, so a
plain GET is enough. `?category=<label>` filters server-side (one category
per request, so several are fetched in turn), `from=<offset>` paginates in
steps of 10, and no `s` param is sent (BMO's category-dropping quirk).

Per-tenant differences this absorbs:

- The job URL is the blob's `applyUrl` (the real backend ATS — Workday for
  RBC/BMO/Adobe/Blizzard, Ashby for Snowflake). Some tenants have no
  `applyUrl` (Bell, OpenText), so `job_url_template` formatted with the
  job's `jobId` is used instead.
- Sites whose category is its own landing page (RBC's `/c/<category>-jobs`,
  Blizzard's `rk=` refinement) pass `categories=None` plus fixed `params`.
  RBC's needs `s=1`; category-param searches must *not* send it (BMO).
- Blizzard's landing page puts the jobs under `targetedJobs` instead of
  `eagerLoadRefineSearch` (`blob_key`).
- Snowflake's `jobId` isn't its stable ID; `reqId` is (`id_field`).
- The default sort isn't fully stable, so pages can overlap — deduped.
- Data roles come from a second search, `?keywords=<term>` on the site's
  search-results page for each of `CORE_SEARCH_TERMS`, keeping only data
  titles. Sites whose category is a landing page pass `search_url`.
"""

import json
import logging
from collections.abc import Callable

import httpx

from .base import CORE_SEARCH_TERMS, NormalizedJob, is_core_title

logger = logging.getLogger(__name__)

MAX_PAGES = 50
DDO_MARKER = "phApp.ddo = "
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}


def scrape_phenom(
    *,
    name: str,
    list_url: str,
    platform: str,
    categories: list[str] | None = None,
    params: dict | None = None,
    search_url: str | None = None,
    job_url_template: str | None = None,
    blob_key: str = "eagerLoadRefineSearch",
    id_field: str = "jobId",
    job_filter: Callable[[dict], bool] | None = None,
) -> list[NormalizedJob]:
    """Fetch each of `categories` via `?category=` (or `list_url` as-is if
    None), with `params` added to every request. `job_filter(raw_job)` can
    drop jobs client-side (e.g. by `country`), including keyword-search ones.
    `search_url` is the site's search-results page for the keyword searches;
    it defaults to `list_url`, which is one already when `categories` is
    used."""
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()

    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:

        def scrape_pass(url: str, base_params: dict, key: str, data_only: bool, label: str) -> None:
            """One paged listing. With `data_only`, only core titles (data, ML, software) are
            kept, and paging stops at the first page without one (keyword
            results are sorted by relevance)."""
            offset = 0
            for _ in range(MAX_PAGES):
                response = client.get(url, params={**base_params, "from": offset})
                response.raise_for_status()
                search = _extract_ddo(response.text, name)[key]
                page_jobs = search["data"]["jobs"]
                if not page_jobs:
                    break
                for raw in page_jobs:
                    job_id = str(raw[id_field])
                    if job_id in seen_ids or (data_only and not is_core_title(raw["title"])):
                        continue
                    seen_ids.add(job_id)
                    if job_filter is None or job_filter(raw):
                        jobs.append(_normalize(raw, job_id, job_url_template, platform))
                offset += len(page_jobs)
                if offset >= search["totalHits"] or (
                    data_only and not any(is_core_title(raw["title"]) for raw in page_jobs)
                ):
                    break
            else:
                logger.warning("%s scrape of %r hit MAX_PAGES=%d", name, label, MAX_PAGES)

        for category in categories or [None]:
            category_params = {**(params or {})}
            if category is not None:
                category_params["category"] = category
            scrape_pass(list_url, category_params, blob_key, data_only=False, label=category)
        for term in CORE_SEARCH_TERMS:
            scrape_pass(search_url or list_url, {"keywords": term}, "eagerLoadRefineSearch", data_only=True, label=term)

    logger.info("%s: fetched %d jobs", name, len(jobs))
    return jobs


def _extract_ddo(html: str, name: str) -> dict:
    idx = html.find(DDO_MARKER)
    if idx == -1:
        raise ValueError(f"Could not find phApp.ddo in {name} page — site structure may have changed")
    ddo, _end = json.JSONDecoder().raw_decode(html, idx + len(DDO_MARKER))
    return ddo


def _normalize(raw: dict, job_id: str, job_url_template: str | None, platform: str) -> NormalizedJob:
    location = "; ".join(raw.get("multi_location") or []) or raw.get("location") or raw.get("cityStateCountry") or ""
    category = " / ".join(p for p in (raw.get("category"), raw.get("subCategory")) if p)
    posted_date = raw.get("postedDate")
    return {
        "external_id": job_id,
        "title": raw["title"].strip(),
        "url": job_url_template.format(job_id=raw["jobId"]) if job_url_template else raw.get("applyUrl") or "",
        "location": location,
        "category": category,
        "posted_date": posted_date[:10] if posted_date else None,
        "platform": platform,
    }
