"""Deloitte Canada careers scraper (technology roles).

careers.deloitte.ca runs SuccessFactors' newer client-rendered career site
("Unify"/rmk-jobs-search), not the server-rendered Jobs2Web pages that
scrapers/jobs2web.py reads. Its job list is a JSON API, found with a
Playwright network capture:
`POST https://careers.deloitte.ca/services/recruiting/v1/jobs` with
`{"locale": "en_US", "pageNumber": N, "sortBy": "date", "keywords": "",
"location": "", "facetFilters": {}, ...}`.

- The page sends an `x-csrf-token` header, but the API also answers
  without one once the session cookie from a GET of `/search/` is set.
- 10 jobs per page, `totalJobs` in the response (423 on 2026-10-02, all
  Canadian).
- No department, service line or category comes back, and the page shows
  no facets. So scope is a title match on technology roles, the same
  heuristic as EY.
- Per job: `id` (external_id), `unifiedStandardTitle`, `mfield1` (list of
  cities), `unifiedStandardStart` (posting date as M/D/YY). The job page is
  `/job/<urlTitle>/<id>-en_US/` (`urlTitle` comes HTML-escaped, e.g. `&amp;`).
"""

import html
import logging
import re
from datetime import datetime

import httpx

from .base import NormalizedJob, is_data_title

logger = logging.getLogger(__name__)

BASE_URL = "https://careers.deloitte.ca"
MAX_PAGES = 80
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"}
TITLE_PATTERN = re.compile(
    r"technolog|software|developer|engineer|data|cloud|cyber|\bAI\b|artificial intelligence|machine learning|"
    r"architect|devops|\bIT\b|digital|automation|salesforce|servicenow|\bSAP\b|technologie|logiciel|donn[ée]es",
    re.IGNORECASE,
)


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    total = 0

    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        client.get(f"{BASE_URL}/search/", params={"q": "", "locale": "en_US"}).raise_for_status()
        for page in range(MAX_PAGES):
            response = client.post(
                f"{BASE_URL}/services/recruiting/v1/jobs",
                json={
                    "locale": "en_US",
                    "pageNumber": page,
                    "sortBy": "date",
                    "keywords": "",
                    "location": "",
                    "facetFilters": {},
                    "brand": "",
                    "skills": [],
                    "categoryId": 0,
                    "alertId": "",
                    "rcmCandidateId": "",
                },
            )
            response.raise_for_status()
            payload = response.json()
            total = payload.get("totalJobs", 0)
            results = [entry["response"] for entry in payload.get("jobSearchResult") or []]
            new = [raw for raw in results if raw["id"] not in seen_ids]
            if not new:
                break
            for raw in new:
                seen_ids.add(raw["id"])
                title = raw.get("unifiedStandardTitle") or ""
                if TITLE_PATTERN.search(title) or is_data_title(title):
                    jobs.append(_normalize(raw))
            if len(seen_ids) >= total:
                break
        else:
            logger.warning("Deloitte scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Deloitte: fetched %d matching jobs (of %d total)", len(jobs), total)
    return jobs


def _normalize(raw: dict) -> NormalizedJob:
    cities = raw.get("mfield1") or []
    location = "; ".join(cities)
    return {
        "external_id": raw["id"],
        "title": raw["unifiedStandardTitle"].strip(),
        "url": f"{BASE_URL}/job/{html.unescape(raw['urlTitle'])}/{raw['id']}-en_US/",
        "location": location,
        "category": "Technology (title match)",
        "posted_date": _parse_date(raw.get("unifiedStandardStart")),
        "platform": "SuccessFactors",
    }


def _parse_date(text: str | None) -> str | None:
    try:
        return datetime.strptime(text or "", "%m/%d/%y").date().isoformat()
    except ValueError:
        return None
