"""Adobe careers scraper (Engineering and Product category, Canada only).

Same Phenom People platform as RBC/BMO (scrapers/rbc.py, scrapers/bmo.py) —
job data is embedded server-side in a `phApp.ddo = {...}` JSON blob, so a
plain HTTP GET is enough, no browser needed. See rbc.py's docstring for the
general shape of this approach.

Adobe-specific notes (see CLAUDE.md's "Intel, Oracle, Spotify, Adobe, Sony,
AMD, Uber scraping approach" section):

- Category filtering is `?category=Engineering and Product` (confirmed
  against the blob's own `category` facet aggregation: exactly matches that
  facet's reported count).
- **Has BMO's pagination quirk, not RBC's**: combining the `category=`
  param with `s=1` silently drops the filter back to the full unfiltered
  set (confirmed live — `s=1` returns the same totalHits as no category at
  all). Omitting `s` and paginating with `from=N` alone works correctly
  (confirmed jobs on paginated pages all carry "Engineering and Product" in
  their `multi_category` array) — so, like bmo.py, this scraper does NOT
  send `s`.
- A job's own `category` field can show a *different* primary category
  (e.g. "Design") even when it matched the "Engineering and Product" filter
  via its `multi_category` array (Adobe jobs can belong to multiple
  categories). `category` is still recorded as-is from the job's own field,
  same convention as every other scraper here (no cross-company
  normalization).
- **No working country query param** — every variant tried returns the
  unfiltered set. Canada jobs are found by fetching the category-filtered
  pages and filtering client-side on each job's own `country` field (full
  name string, e.g. `"Canada"`, `"United States of America"`).
- Every job's `applyUrl` points at `adobe.wd5.myworkdayjobs.com` — same
  Phenom-front/Workday-apply relationship as RBC/BMO. `platform` =
  `"Workday"`.
"""

import json
import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

LIST_URL = "https://careers.adobe.com/us/en/search-results"
CATEGORY = "Engineering and Product"
PAGE_SIZE = 10
DDO_MARKER = "phApp.ddo = "
MAX_PAGES = 100  # safety cap; this category currently has ~324 jobs


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    offset = 0
    total_hits: int | None = None

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for _ in range(MAX_PAGES):
            # Deliberately no "s" param — see module docstring's pagination quirk.
            response = client.get(LIST_URL, params={"category": CATEGORY, "from": offset})
            response.raise_for_status()

            search = _extract_ddo(response.text)["eagerLoadRefineSearch"]
            total_hits = search["totalHits"]
            page_jobs = search["data"]["jobs"]
            if not page_jobs:
                break

            for raw in page_jobs:
                job_id = raw["jobId"]
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                if raw.get("country") != "Canada":
                    continue
                jobs.append(_normalize(raw))

            offset += PAGE_SIZE
            if offset >= total_hits:
                break
        else:
            logger.warning("Adobe scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Adobe: fetched %d Canada jobs (site reported totalHits=%s)", len(jobs), total_hits)
    return jobs


def _extract_ddo(html: str) -> dict:
    idx = html.find(DDO_MARKER)
    if idx == -1:
        raise ValueError("Could not find phApp.ddo in Adobe page — site structure may have changed")
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
        "external_id": raw["jobId"],
        "title": raw["title"],
        "url": raw["applyUrl"],
        "location": location,
        "category": raw.get("category", ""),
        "posted_date": posted_date[:10] if posted_date else None,
        "platform": "Workday",
    }
