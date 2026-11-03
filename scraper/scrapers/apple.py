"""Apple careers scraper (Canada / Software and Services team).

jobs.apple.com is fully open, unauthenticated, and no bot-blocking was
encountered. It looks like a client-rendered React app, but each search page
is actually server-rendered: the results are embedded in a
`window.__staticRouterHydrationData = JSON.parse("...")` assignment inside a
`<script>` tag — a React-Router-flavored variant of the "one big embedded
JSON blob" pattern used by RBC's `phApp.ddo` (see rbc.py), just double-encoded
(the blob is a JSON string *containing* escaped JSON text, since it's the
argument to `JSON.parse(...)` rather than a bare object literal like RBC's).
See CLAUDE.md's "Meta, Amazon, Google, Apple, Microsoft, IBM, Canonical
scraping approach" section (Apple bullet) for how this was found.

- `location=canada-CANC` is a real, confirmed server-side filter (live-tested
  2026-09-21: 29 total Canada jobs).
- **No working category/team URL param** — `team=`/`teams=`/`role=` don't
  change `totalRecords`; only free-text `search=` does, with the same
  off-target-hit problem as Google's `q=` search. So this scraper fetches
  the unfiltered `location=canada-CANC` result set and filters client-side on
  each job's own `team.teamName == "Software and Services"` field, which is
  present on every job object even though it isn't an exposed URL filter.
- Pagination: `page=N`, 1-indexed, page size 20 (confirmed live: 29 total ->
  20 on page 1, 9 on page 2).
- Multi-location postings are pre-split by Apple into one search-result
  entry per location, each with its own `id` (e.g. "200674232-2550" and
  "200674232-3965" for the same underlying requisition "200674232" in two
  cities) — `id` is used as `external_id` since it's what's actually unique
  per listed row, and matches the path segment Apple's own detail links use.
- Detail URL shape confirmed from real links embedded in the page:
  `https://jobs.apple.com/en-us/details/<id>/<transformedPostingTitle>`.
- `postDateInGMT` is a real ISO datetime — used as `posted_date` (date part
  only).
"""

import json
import logging

import httpx

from .base import NormalizedJob, is_data_title

logger = logging.getLogger(__name__)

SEARCH_URL = "https://jobs.apple.com/en-us/search"
DETAIL_URL_TEMPLATE = "https://jobs.apple.com/en-us/details/{id}/{slug}"
LOCATION = "canada-CANC"
TEAM_NAME = "Software and Services"

HYDRATION_MARKER = 'window.__staticRouterHydrationData = JSON.parse("'
HYDRATION_END_MARKER = '");</script>'

PAGE_SIZE = 20
MAX_PAGES = 50  # safety cap; this filter currently returns ~2 pages


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    total: int | None = None

    with httpx.Client(timeout=30) as client:
        for page in range(1, MAX_PAGES + 1):
            response = client.get(SEARCH_URL, params={"location": LOCATION, "page": page})
            response.raise_for_status()

            search = _extract_search_data(response.text)
            if total is None:
                total = search["totalRecords"]
            results = search["searchResults"]
            if not results:
                break

            for raw in results:
                job_id = raw["id"]
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                if raw.get("team", {}).get("teamName") != TEAM_NAME and not is_data_title(raw["postingTitle"]):
                    continue
                jobs.append(_normalize(raw))

            if page * PAGE_SIZE >= total:
                break
        else:
            logger.warning("Apple scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Apple: fetched %d Canada + %s jobs (site reported totalRecords=%s)", len(jobs), TEAM_NAME, total)
    return jobs


def _extract_search_data(html: str) -> dict:
    idx = html.find(HYDRATION_MARKER)
    if idx == -1:
        raise ValueError("Could not find __staticRouterHydrationData in Apple page — site structure may have changed")
    start = idx + len(HYDRATION_MARKER)
    end = html.find(HYDRATION_END_MARKER, start)
    if end == -1:
        raise ValueError("Could not find end of __staticRouterHydrationData blob in Apple page")

    # The blob is a JSON string literal (argument to JSON.parse(...)), so it
    # must be unescaped once (wrap it back into a JSON string and decode) to
    # get the real JSON text, then decoded again to get the actual object.
    raw = html[start:end]
    json_text = json.loads('"' + raw + '"')
    data = json.loads(json_text)
    return data["loaderData"]["search"]


def _normalize(raw: dict) -> NormalizedJob:
    locations = raw.get("locations") or []
    location = ", ".join(loc["name"] for loc in locations if loc.get("name")) or "Canada"
    posted_date = raw.get("postDateInGMT")
    return {
        "external_id": raw["id"],
        "title": raw["postingTitle"],
        "url": DETAIL_URL_TEMPLATE.format(id=raw["id"], slug=raw.get("transformedPostingTitle", "")),
        "location": location,
        "category": raw.get("team", {}).get("teamName", TEAM_NAME),
        "posted_date": posted_date[:10] if posted_date else None,
        "platform": "Apple Jobs (custom, in-house)",
    }
