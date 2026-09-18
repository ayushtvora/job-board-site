"""BMO careers scraper (Technology category).

Same Phenom People platform as RBC (scrapers/rbc.py) — job data for each
page of results is embedded server-side in a `phApp.ddo = {...}` JSON
blob, so a plain HTTP GET is enough, no browser needed. See rbc.py's
docstring for the general shape of this approach.

BMO-specific notes:

- The `/ca/en/` site section is Canada-only already (confirmed: the site's
  own `country` facet reports 100% "Canada" across all 597 unfiltered
  jobs), so no separate country filter is needed to satisfy "Country:
  Canada" — unlike RBC, which has no such per-country split.
- Category filtering is a plain human-readable query param,
  `?category=Technology` — matches the `category` facet's label exactly
  (confirmed: filtering drops totalHits from 597 to 63, matching that
  facet's own reported count). No opaque ID involved, unlike Workday's
  facets.
- **Pagination quirk**: RBC's `&s=1` pagination param, when combined with
  `category=...` here, silently drops the category filter entirely (reverts
  to the full unfiltered 597). Omitting `s` and paginating with `from=N`
  alone works correctly with the filter applied (confirmed jobs on
  paginated pages are all distinct `Technology` jobs) — so BMO's scraper
  deliberately does NOT send `s`, unlike RBC's.
- Same per-job fields as RBC's blob: `jobId`, `title`, `postedDate`,
  `category`, `location`, `applyUrl` (`*.wd3.myworkdayjobs.com` for every
  job seen). **`platform` = `"Workday"`** for BMO, same as RBC.
"""

import json
import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

LIST_URL = "https://jobs.bmo.com/ca/en/search-results"
CATEGORY = "Technology"
PAGE_SIZE = 10
DDO_MARKER = "phApp.ddo = "
MAX_PAGES = 50  # safety cap; this category currently has ~63 jobs


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    offset = 0
    total_hits: int | None = None

    with httpx.Client(timeout=30) as client:
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
                jobs.append(_normalize(raw))

            offset += PAGE_SIZE
            if offset >= total_hits:
                break
        else:
            logger.warning("BMO scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("BMO: fetched %d jobs (site reported totalHits=%s)", len(jobs), total_hits)
    return jobs


def _extract_ddo(html: str) -> dict:
    idx = html.find(DDO_MARKER)
    if idx == -1:
        raise ValueError("Could not find phApp.ddo in BMO page — site structure may have changed")
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
