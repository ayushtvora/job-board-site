"""Shared helper for iCIMS "Jibe" career-site scrapers (Kinaxis, AMD).

Jibe front-ends (job URLs like `/jobs/<reqId>?lang=en-us`, apply links to
`<tenant>.icims.com`) serve their listing as open JSON:
`GET <base_url>/api/jobs?page=N&internal=false` (no auth, 10 jobs per page,
`totalCount` in the response, each job wrapped as `{"data": {...}}`).

- `job_filter` sees every posting, so it's where each tenant keeps data
  titles (`base.is_data_title`) alongside its categories.
- Some tenants accept server-side filters as extra query params (AMD's
  `location=Canada` narrows 1,000+ jobs to the Canadian ones); pass them in
  `params`. Everything else is filtered client-side with `job_filter`.
- `category` is a list with stray leading spaces (`[" Engineering"]`),
  stripped by `categories()`.
- Fields: `req_id` (stable iCIMS requisition ID, external_id), `title`,
  `full_location`, `country_code`, `posted_date` (ISO datetime), `slug`,
  `description` (HTML; `responsibilities`/`qualifications` repeat parts
  of it, so they're only a fallback).
- `platform` = "iCIMS" (`ats_code` on every job).
"""

import logging
from collections.abc import Callable

import httpx

from .base import NormalizedJob, clean_description

logger = logging.getLogger(__name__)

MAX_PAGES = 100
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"}


def scrape_jibe(
    *,
    name: str,
    base_url: str,
    job_path: str,
    job_filter: Callable[[dict], bool],
    params: dict[str, str] | None = None,
) -> list[NormalizedJob]:
    """`job_path` is the job page path under `base_url`, e.g. "/jobs" or
    "/careers-home/jobs"."""
    jobs: list[NormalizedJob] = []
    seen = 0
    total = 0

    with httpx.Client(timeout=30, headers=HEADERS) as client:
        for page in range(1, MAX_PAGES + 1):
            response = client.get(f"{base_url}/api/jobs", params={"page": page, "internal": "false", **(params or {})})
            response.raise_for_status()
            payload = response.json()
            total = payload.get("totalCount", 0)
            page_jobs = [entry["data"] for entry in payload.get("jobs") or []]
            if not page_jobs:
                break
            seen += len(page_jobs)
            jobs.extend(_normalize(raw, base_url, job_path) for raw in page_jobs if job_filter(raw))
            if seen >= total:
                break
        else:
            logger.warning("%s scrape hit MAX_PAGES=%d without finishing — got %d jobs", name, MAX_PAGES, len(jobs))

    logger.info("%s: fetched %d matching jobs (of %d total)", name, len(jobs), total)
    return jobs


def categories(raw: dict) -> list[str]:
    return [c.strip() for c in raw.get("category") or []]


def _normalize(raw: dict, base_url: str, job_path: str) -> NormalizedJob:
    posted = raw.get("posted_date")
    return {
        "external_id": str(raw["req_id"]),
        "title": raw["title"].strip(),
        "url": f"{base_url}{job_path}/{raw['slug']}?lang=en-us",
        "location": raw.get("full_location") or "",
        "category": ", ".join(categories(raw)),
        "posted_date": posted[:10] if posted else None,
        "platform": "iCIMS",
        "description": clean_description(
            raw.get("description") or (raw.get("responsibilities") or "") + (raw.get("qualifications") or "")
        ),
    }
