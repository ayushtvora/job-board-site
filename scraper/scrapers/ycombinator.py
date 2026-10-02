"""Y Combinator careers scraper (Canada / roles at YC itself).

This tracks jobs at Y Combinator the employer, like every other company
here, not the thousands of startup jobs on YC's Work at a Startup board.

`ycombinator.com/companies/y-combinator/jobs` is an Inertia.js page: the
job list is JSON in the root element's `data-page` attribute
(`props.jobPostings`), so one plain GET is enough.

- 8 postings on 2026-10-02, all in San Francisco, so an empty result is
  expected.
- Per posting: `id` (external_id), `title`, `url` (relative), `location`,
  `role` / `prettyRole` (e.g. "Engineering", used for scope and category).
  `createdAt` is relative text ("2 months ago"), so there's no posted date.
"""

import html
import json
import logging
import re

import httpx

from .base import CANADA_PATTERN, NormalizedJob

logger = logging.getLogger(__name__)

JOBS_URL = "https://www.ycombinator.com/companies/y-combinator/jobs"
DATA_PAGE_RE = re.compile(r'data-page="([^"]*)"')
ROLES = {"eng", "engineering", "software", "data", "science", "design"}
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"}


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        response = client.get(JOBS_URL)
        response.raise_for_status()
    match = DATA_PAGE_RE.search(response.text)
    if not match:
        raise RuntimeError("YC jobs page no longer embeds its Inertia data-page JSON")
    postings = json.loads(html.unescape(match.group(1)))["props"]["jobPostings"]

    jobs = [
        _normalize(raw)
        for raw in postings
        if (raw.get("role") or "").lower() in ROLES and CANADA_PATTERN.search(raw.get("location") or "")
    ]
    logger.info("Y Combinator: fetched %d matching jobs (of %d postings)", len(jobs), len(postings))
    return jobs


def _normalize(raw: dict) -> NormalizedJob:
    return {
        "external_id": str(raw["id"]),
        "title": raw["title"].strip(),
        "url": f"https://www.ycombinator.com{raw['url']}",
        "location": raw.get("location") or "",
        "category": raw.get("prettyRole") or "",
        "posted_date": None,
        "platform": "Y Combinator (custom, in-house)",
    }
