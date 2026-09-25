"""Snowflake careers scraper (Engineering category, Canada only).

Same Phenom People platform as RBC/BMO (scrapers/rbc.py, scrapers/bmo.py) —
job data is embedded server-side in a `phApp.ddo = {...}` JSON blob, so a
plain HTTP GET is enough, no browser needed. See rbc.py's docstring for the
general shape of this approach.

Snowflake-specific notes (see CLAUDE.md's "Snowflake scraping approach"
section):

- The job list lives at `ddo["eagerLoadRefineSearch"]["data"]["jobs"]` —
  confirmed live 2026-09-21 this is the *same* path RBC/BMO use (CLAUDE.md's
  note calling it "a different path than RBC's" doesn't hold up against the
  live blob; documenting the discrepancy here rather than re-guessing).
- Category filtering is `?category=Engineering` (confirmed against the
  blob's own totalHits, currently 95).
- Pagination: `from=<offset>` in steps of 10, no `s` param needed — same
  convention as RBC (not BMO's category-drops-with-`s` quirk; not tested
  with `s` here since omitting it already works cleanly).
- **No working country-level filter** — Canada jobs are found by fetching
  the category-filtered pages and filtering client-side on each job's own
  `country` field (plain country name, e.g. `"Canada"`).
- **No `jobId` field in this tenant's blob** (unlike RBC/BMO/Blizzard/Adobe)
  — the stable per-job identifier here is `reqId` (e.g. `"REQ18507"` or
  `"ASHREQ-7477"`), used as `external_id`.
- Every job's `applyUrl` points at `jobs.ashbyhq.com/snowflake/<uuid>` with
  `externalApply: true` — Snowflake's real underlying ATS is **Ashby**, not
  Workday (the Phenom front-end is purely a listing/branding layer, same
  relationship pattern as RBC/BMO/Manulife's Phenom-front/other-ATS-apply).
  `platform` = `"Ashby"`.
"""

import json
import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

LIST_URL = "https://careers.snowflake.com/us/en/search-results"
CATEGORY = "Engineering"
PAGE_SIZE = 10
DDO_MARKER = "phApp.ddo = "
MAX_PAGES = 50  # safety cap; this category currently has ~95 jobs


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    offset = 0
    total_hits: int | None = None

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for _ in range(MAX_PAGES):
            response = client.get(LIST_URL, params={"category": CATEGORY, "from": offset})
            response.raise_for_status()

            search = _extract_ddo(response.text)["eagerLoadRefineSearch"]
            total_hits = search["totalHits"]
            page_jobs = search["data"]["jobs"]
            if not page_jobs:
                break

            for raw in page_jobs:
                req_id = raw["reqId"]
                if req_id in seen_ids:
                    continue
                seen_ids.add(req_id)
                if raw.get("country") != "Canada":
                    continue
                jobs.append(_normalize(raw))

            offset += PAGE_SIZE
            if offset >= total_hits:
                break
        else:
            logger.warning("Snowflake scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Snowflake: fetched %d Canada jobs (site reported totalHits=%s)", len(jobs), total_hits)
    return jobs


def _extract_ddo(html: str) -> dict:
    idx = html.find(DDO_MARKER)
    if idx == -1:
        raise ValueError("Could not find phApp.ddo in Snowflake page — site structure may have changed")
    start = idx + len(DDO_MARKER)
    ddo, _end = json.JSONDecoder().raw_decode(html, start)
    return ddo


def _normalize(raw: dict) -> NormalizedJob:
    location = (
        raw.get("location")
        or ", ".join(raw.get("multi_location", []))
        or raw.get("cityStateCountry", "")
    )
    posted_date = raw.get("postedDate")
    return {
        "external_id": raw["reqId"],
        "title": raw["title"],
        "url": raw["applyUrl"],
        "location": location,
        "category": raw.get("category", ""),
        "posted_date": posted_date[:10] if posted_date else None,
        "platform": "Ashby",
    }
