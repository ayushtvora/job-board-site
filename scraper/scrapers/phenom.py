"""Shared helper for Phenom People career-site scrapers (the fourth wave onward).

Same `phApp.ddo` blob approach as RBC/BMO (scrapers/rbc.py, scrapers/bmo.py
— see CLAUDE.md's "RBC scraping approach"): each search-results page embeds
its job list as JSON at `phApp.ddo.eagerLoadRefineSearch.data.jobs`, so a
plain GET is enough. `?category=<label>` filters server-side (one category
per request, so several are fetched in turn), `from=<offset>` paginates in
steps of 10, and no `s` param is sent (BMO's category-dropping quirk).

Some Phenom tenants have no `applyUrl` in the blob (the backend ATS is
reached through Phenom's own job page instead), so the job URL comes from
`job_url_template` formatted with the job's `jobId`.

Not used by the pre-existing Phenom scrapers (rbc, bmo, blizzard, adobe,
snowflake), which predate it.
"""

import json
import logging
from collections.abc import Callable

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

PAGE_SIZE = 10
MAX_PAGES = 50
DDO_MARKER = "phApp.ddo = "
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}


def scrape_phenom(
    *,
    name: str,
    list_url: str,
    job_url_template: str,
    categories: list[str],
    platform: str,
    job_filter: Callable[[dict], bool] | None = None,
) -> list[NormalizedJob]:
    """`job_filter(raw_job)` can drop jobs client-side (e.g. by `country`)."""
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()

    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        for category in categories:
            offset = 0
            for _ in range(MAX_PAGES):
                response = client.get(list_url, params={"category": category, "from": offset})
                response.raise_for_status()
                search = _extract_ddo(response.text, name)["eagerLoadRefineSearch"]
                page_jobs = search["data"]["jobs"]
                if not page_jobs:
                    break
                for raw in page_jobs:
                    if raw["jobId"] in seen_ids:
                        continue
                    seen_ids.add(raw["jobId"])
                    if job_filter is None or job_filter(raw):
                        jobs.append(_normalize(raw, job_url_template, platform))
                offset += PAGE_SIZE
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


def _normalize(raw: dict, job_url_template: str, platform: str) -> NormalizedJob:
    location = "; ".join(raw.get("multi_location") or []) or raw.get("location") or raw.get("cityStateCountry") or ""
    category = " / ".join(p for p in (raw.get("category"), raw.get("subCategory")) if p)
    posted_date = raw.get("postedDate")
    return {
        "external_id": str(raw["jobId"]),
        "title": raw["title"].strip(),
        "url": job_url_template.format(job_id=raw["jobId"]),
        "location": location,
        "category": category,
        "posted_date": posted_date[:10] if posted_date else None,
        "platform": platform,
    }
