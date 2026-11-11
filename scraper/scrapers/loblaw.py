"""Loblaw Companies careers scraper (Technology and Business Analytics, plus
tech/data titles anywhere).

careers.loblaw.ca moved to a **Paradox** career site by 2026-11-10 (assets
from cdn.sites.paradox.ai; applying goes through olivia.paradox.ai). It
lists every Loblaw posting, ~3,900 of them, almost all store and
distribution jobs. The Workday sites this scraper used to read
(`myview.wd3.myworkdayjobs.com`, sites `Loblaw-Digital_Careers_Carrieres`
and `loblaw_careers`) both report 0 postings now, and `Careers` there only
has a handful of store jobs.

- The page is server-rendered, but its `?category=` URL param is ignored;
  filtering goes through the JSON API the page itself calls:
  `POST /api/get-jobs?page_number=N&page_size=10&filter[category][0]=...`
  (or `&keyword=...`) with body `{"site_available_languages": ["en"]}`.
  It returns 200 only with the cookies set by first loading `/jobs`
  (Akamai `bm_*` plus Paradox's `ct`). `page_size` is capped at 10.
- Scope: the `category` facet's "Technology" and "Business Analytics"
  values (22 postings on 2026-11-10: data engineers and scientists,
  software engineering managers, technical product managers), plus a
  keyword search for each of `base.CORE_SEARCH_TERMS` keeping
  `base.is_core_title` titles, which finds co-ops and analysts filed under
  "Business Support" or "Digital & Ecommerce". Keyword results are sorted
  by relevance, so paging stops at the first page without one.
- Fields: `reference` is the Workday-style req ID ("R2000726808"), used as
  external_id. Location is from `locations[]` (`city`, `state`). The
  description is inline (HTML). There's no posted date anywhere.
- The job page is `https://careers.loblaw.ca/<originalURL>`.
"""

import logging

import httpx

from .base import CORE_SEARCH_TERMS, NormalizedJob, clean_description, is_core_title

logger = logging.getLogger(__name__)

SITE = "https://careers.loblaw.ca"
API_URL = f"{SITE}/api/get-jobs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "application/json",
    "Origin": SITE,
    "Referer": f"{SITE}/jobs",
}
CATEGORIES = ["Technology", "Business Analytics"]
PAGE_SIZE = 10  # the API's maximum
MAX_PAGES = 30


def scrape() -> list[NormalizedJob]:
    jobs: dict[str, NormalizedJob] = {}
    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        # Sets the cookies the API requires.
        client.get(f"{SITE}/jobs").raise_for_status()

        def scrape_pass(params: list[tuple[str, str]], keyword_only: bool) -> None:
            for page in range(1, MAX_PAGES + 1):
                response = client.post(
                    API_URL,
                    params=[("page_number", str(page)), ("page_size", str(PAGE_SIZE)), *params],
                    json={"site_available_languages": ["en"]},
                )
                response.raise_for_status()
                payload = response.json()
                page_jobs = payload["jobs"]
                for raw in page_jobs:
                    if keyword_only and not is_core_title(raw["title"]):
                        continue
                    job = _normalize(raw, "Keyword search" if keyword_only else _family(raw))
                    jobs.setdefault(job["external_id"], job)
                if page * PAGE_SIZE >= payload["totalJob"] or (
                    keyword_only and not any(is_core_title(raw["title"]) for raw in page_jobs)
                ):
                    break
            else:
                logger.warning("Loblaw scrape of %s hit MAX_PAGES=%d", params, MAX_PAGES)

        scrape_pass([(f"filter[category][{i}]", category) for i, category in enumerate(CATEGORIES)], keyword_only=False)
        for term in CORE_SEARCH_TERMS:
            scrape_pass([("keyword", term)], keyword_only=True)

    logger.info("Loblaw: fetched %d jobs", len(jobs))
    return list(jobs.values())


def _family(raw: dict) -> str | None:
    return next((field["value"] for field in raw.get("customFields", []) if field.get("cfKey") == "cf_job_family"), None)


def _normalize(raw: dict, category: str | None) -> NormalizedJob:
    places = []
    for location in raw.get("locations") or []:
        place = ", ".join(part for part in (location.get("city"), location.get("state"), location.get("country")) if part)
        if place and place not in places:
            places.append(place)
    return {
        "external_id": raw["reference"],
        "title": raw["title"],
        "url": f"{SITE}/{raw['originalURL'].lstrip('/')}",
        "location": "; ".join(places),
        "category": category or "Loblaw",
        "posted_date": None,
        "platform": "Paradox",
        "description": clean_description(raw.get("description")),
    }
