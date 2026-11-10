"""Amazon careers scraper (Canada / Software Development category, plus data roles).

Amazon's own careers site (amazon.jobs) exposes a fully open, unauthenticated
JSON search API — no third-party ATS, no bot-blocking encountered. See
CLAUDE.md's "Meta, Amazon, Google, Apple, Microsoft, IBM, Canonical scraping
approach" section (Amazon bullet) for how this was found.

- `GET https://www.amazon.jobs/en/search.json` takes `category[]=` (array
  form) and `country=` (singular form) — confirmed the *only* two forms that
  actually filter server-side; the opposite forms (`category=` singular,
  `country[]=` array) are silently ignored, so those exact param names/forms
  matter.
- Only `country=` is sent: Canada has a few hundred postings in all
  (382 on 2026-11-02), so they're all read and scoped client-side to
  the Software Development `job_category` or a data title. Data roles
  are spread over several categories (Data Science, Business
  Intelligence, Applied Science, ...).
- Pagination is `offset`/`result_limit` in the query string; the response's
  `hits` field is the total match count — only trusted from the first page,
  per the same caution as the Workday scrapers (TD's `total` bug).
- `id_icims` is a legacy field name (Amazon's own system isn't actually
  iCIMS) but is still the real stable per-job ID — used as `external_id`.
- `posted_date` comes back as a human-readable string (e.g.
  "September 21, 2026"), not ISO — parsed and normalized to "YYYY-MM-DD".
- `job_path` is relative (e.g. "/en/jobs/<id>/<slug>") — prefixed with the
  site's own domain to form the full URL.
"""

import logging
from datetime import datetime

import httpx

from .base import NormalizedJob, clean_description, is_data_title

logger = logging.getLogger(__name__)

BASE_URL = "https://www.amazon.jobs"
SEARCH_URL = f"{BASE_URL}/en/search.json"
CATEGORY_LABEL = "Software Development"
COUNTRY = "CAN"

PAGE_SIZE = 20
MAX_PAGES = 100  # safety cap; ~179 jobs / 20 per page is ~9 pages today


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    offset = 0
    total: int | None = None

    with httpx.Client(timeout=30) as client:
        for _ in range(MAX_PAGES):
            response = client.get(
                SEARCH_URL,
                params={
                    "country": COUNTRY,
                    "result_limit": PAGE_SIZE,
                    "offset": offset,
                },
            )
            response.raise_for_status()
            payload = response.json()
            # Only trust `hits` from the first page — mirrors the Workday
            # scrapers' caution around `total` after the TD bug.
            if total is None:
                total = payload["hits"]
            postings = payload["jobs"]
            if not postings:
                break

            for raw in postings:
                job_id = raw["id_icims"]
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                if raw.get("job_category") == CATEGORY_LABEL or is_data_title(raw["title"]):
                    jobs.append(_normalize(raw))

            offset += PAGE_SIZE
            if offset >= total:
                break
        else:
            logger.warning("Amazon scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Amazon: fetched %d matching jobs (of %s Canadian postings)", len(jobs), total)
    return jobs


def _normalize(raw: dict) -> NormalizedJob:
    location = raw.get("normalized_location") or ", ".join(
        part for part in (raw.get("city"), raw.get("state"), raw.get("country_code")) if part
    )
    return {
        "external_id": raw["id_icims"],
        "title": raw["title"],
        "url": BASE_URL + raw["job_path"],
        "location": location,
        "category": raw.get("job_category", CATEGORY_LABEL),
        "posted_date": _parse_posted_date(raw.get("posted_date")),
        "platform": "Amazon Jobs (custom, in-house)",
        # search.json carries the full posting, split into three HTML fields.
        "description": clean_description(
            f"{raw.get('description') or ''}"
            f"<h3>Basic qualifications</h3>{raw.get('basic_qualifications') or ''}"
            f"<h3>Preferred qualifications</h3>{raw.get('preferred_qualifications') or ''}"
        ),
    }


def _parse_posted_date(raw_date: str | None) -> str | None:
    if not raw_date:
        return None
    try:
        return datetime.strptime(raw_date, "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        logger.warning("Amazon: could not parse posted_date %r", raw_date)
        return None
