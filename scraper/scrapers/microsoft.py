"""Microsoft careers scraper, scoped to Canada + Software Engineering.

Real careers URL resolves to `https://apply.careers.microsoft.com/careers`,
a client-rendered SPA. Platform: Eightfold, confirmed via response headers
(`x-ef-ns: smartapply`, `x-ef-req-endpoint`, `x-ef-trace-id`) and a CSP
referencing `docs.eightfold.ai`. See CLAUDE.md's "Meta, Amazon, Google,
Apple, Microsoft, IBM, Canonical scraping approach" section (Microsoft
bullet) for how this was found.

- Real search API: `GET .../api/pcsx/search?domain=microsoft.com&query=<text>&location=<text>&start=<offset>`.
  `query` and `location` are plain free-text params, no opaque facet IDs.
  `location=Canada` alone is confirmed to return real Canadian jobs (~63 at
  investigation time).
- **No working `department=` facet param** (silently ignored) — this
  scraper fetches `location=Canada` unfiltered and filters client-side on
  each job's own `department == "Software Engineering"` field.
- Pagination: `start=` offset, page size 10 — loop until an empty page.
"""

import logging
from datetime import datetime, timezone

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://apply.careers.microsoft.com"
SEARCH_URL = f"{BASE_URL}/api/pcsx/search"

DOMAIN = "microsoft.com"
LOCATION_FILTER = "Canada"
DEPARTMENT_FILTER = "Software Engineering"

PAGE_SIZE = 10
MAX_PAGES = 50  # safety cap; ~63 Canada jobs / 10 per page is ~7 pages today

# A plain httpx request with no User-Agent risks looking like a bot to
# Eightfold's front door; a normal browser-like UA avoids that.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    start = 0

    with httpx.Client(timeout=30, headers=HEADERS) as client:
        for _ in range(MAX_PAGES):
            response = client.get(
                SEARCH_URL,
                params={
                    "domain": DOMAIN,
                    "query": "",
                    "location": LOCATION_FILTER,
                    "start": start,
                },
            )
            response.raise_for_status()
            payload = response.json()
            # Real shape: {"status": 200, "error": {...}, "data": {"positions": [...], "count": N, ...}}
            postings = (payload.get("data") or {}).get("positions") or []
            if not postings:
                break

            for raw in postings:
                if raw.get("department") != DEPARTMENT_FILTER:
                    continue
                job_id = raw.get("displayJobId") or raw.get("atsJobId") or raw.get("id")
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                jobs.append(_normalize(raw))

            start += PAGE_SIZE
        else:
            logger.warning("Microsoft scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Microsoft: fetched %d Canada + Software Engineering jobs", len(jobs))
    return jobs


def _normalize(raw: dict) -> NormalizedJob:
    locations = raw.get("locations")
    if isinstance(locations, list):
        location = ", ".join(locations)
    else:
        location = locations or ""

    posted_ts = raw.get("postedTs")
    posted_date = None
    if posted_ts:
        posted_date = datetime.fromtimestamp(posted_ts, tz=timezone.utc).strftime("%Y-%m-%d")

    position_url = raw.get("positionUrl", "")
    if position_url and not position_url.startswith("http"):
        position_url = f"{BASE_URL}{position_url}"

    job_id = raw.get("displayJobId") or raw.get("atsJobId") or raw.get("id")

    return {
        "external_id": str(job_id),
        "title": raw.get("name", ""),
        "url": position_url,
        "location": location,
        "category": raw.get("department", ""),
        "posted_date": posted_date,
        "platform": "Eightfold",
    }
