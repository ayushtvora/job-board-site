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
"""

import json
import logging
from collections.abc import Callable

import httpx

from .base import NormalizedJob

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
    job_url_template: str | None = None,
    blob_key: str = "eagerLoadRefineSearch",
    id_field: str = "jobId",
    job_filter: Callable[[dict], bool] | None = None,
) -> list[NormalizedJob]:
    """Fetch each of `categories` via `?category=` (or `list_url` as-is if
    None), with `params` added to every request. `job_filter(raw_job)` can
    drop jobs client-side (e.g. by `country`)."""
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()

    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        for category in categories or [None]:
            offset = 0
            for _ in range(MAX_PAGES):
                request_params = {**(params or {}), "from": offset}
                if category is not None:
                    request_params["category"] = category
                response = client.get(list_url, params=request_params)
                response.raise_for_status()
                search = _extract_ddo(response.text, name)[blob_key]
                page_jobs = search["data"]["jobs"]
                if not page_jobs:
                    break
                for raw in page_jobs:
                    job_id = str(raw[id_field])
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)
                    if job_filter is None or job_filter(raw):
                        jobs.append(_normalize(raw, job_id, job_url_template, platform))
                offset += len(page_jobs)
                if offset >= search["totalHits"]:
                    break
            else:
                logger.warning("%s scrape of %r hit MAX_PAGES=%d", name, category, MAX_PAGES)

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
