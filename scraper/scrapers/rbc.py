"""RBC careers scraper (Technology | Analytics | Research category).

The site (Phenom People's Career Site Builder) looks JS-rendered, but each
page's job results are actually embedded server-side in a `phApp.ddo = {...}`
JSON assignment inside a <script> tag — no browser/JS execution needed, a
plain HTTP GET is enough. See CLAUDE.md's "RBC scraping approach" section
for how this was found.
"""

import json
import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

CATEGORY_URL = "https://jobs.rbc.com/ca/en/c/technology-analytics-research-jobs"
PAGE_SIZE = 10
DDO_MARKER = "phApp.ddo = "
MAX_PAGES = 200  # safety cap; ~312 jobs / 10 per page is ~32 pages today


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    offset = 0
    total_hits: int | None = None

    with httpx.Client(timeout=30) as client:
        for _ in range(MAX_PAGES):
            response = client.get(CATEGORY_URL, params={"from": offset, "s": 1})
            response.raise_for_status()

            search = _extract_ddo(response.text)["eagerLoadRefineSearch"]
            total_hits = search["totalHits"]
            page_jobs = search["data"]["jobs"]
            if not page_jobs:
                break

            for raw in page_jobs:
                job_id = raw["jobId"]
                # Pagination isn't fully stable under the site's default
                # sort, so consecutive pages can overlap slightly.
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                jobs.append(_normalize(raw))

            offset += PAGE_SIZE
            if offset >= total_hits:
                break
        else:
            logger.warning("RBC scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("RBC: fetched %d jobs (site reported totalHits=%s)", len(jobs), total_hits)
    return jobs


def _extract_ddo(html: str) -> dict:
    idx = html.find(DDO_MARKER)
    if idx == -1:
        raise ValueError("Could not find phApp.ddo in RBC page — site structure may have changed")
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
