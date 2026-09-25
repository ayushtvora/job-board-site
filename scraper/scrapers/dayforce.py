"""Shared helper for Dayforce (Ceridian) candidate-portal scrapers.

Dayforce career sites (`jobs.dayforcehcm.com/<locale>/<namespace>/<board>`)
are a Next.js app that loads jobs client-side from a JSON API — found via
a Playwright network capture (2026-09-25):

- `POST https://jobs.dayforcehcm.com/api/geo/<namespace>/jobposting/search`
  with `{"clientNamespace", "jobBoardCode", "cultureCode", "distanceUnit",
  "paginationStart"}` → `{"maxCount", "count", "jobPostings": [...]}`, 25 per
  page, paginated by `paginationStart` (an offset).
- **Requires a NextAuth CSRF token**: without it the API 403s (and looks
  like a Cloudflare block, but isn't). `GET /api/auth/csrf` returns
  `{"csrfToken": ...}` and sets the matching cookie; send the token back as
  an `x-csrf-token` header on the same client. No browser needed.
- Department filter: `departmentId` — a **single** integer (a list 400s),
  found in the page's JS bundle. IDs + names come from
  `GET /api/geo/<ns>/postingattributes/departments/<ns>/<jobBoardId>/<locale>`,
  so scrapers pick departments by name at runtime, one search per department.
- Per posting: `jobPostingId` (used as `external_id` — a requisition can
  have several postings), `jobReqId`, `jobTitle`, `postingStartTimestampUTC`
  (real posted date), `postingLocations[]` with `isoCountryCode`
  (e.g. "CA") and `formattedAddress`. No department on the posting itself.
"""

import logging
from collections.abc import Callable

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://jobs.dayforcehcm.com"
CULTURE = "en-US"
PAGE_SIZE = 25
MAX_PAGES = 40
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}


def scrape_dayforce(
    *,
    name: str,
    namespace: str,
    board: str = "CANDIDATEPORTAL",
    job_board_id: int = 1,
    department_filter: Callable[[str], bool] | None = None,
    country_code: str = "CA",
) -> list[NormalizedJob]:
    """`department_filter(name)` selects departments to search; None = all jobs."""
    search_url = f"{BASE_URL}/api/geo/{namespace}/jobposting/search"
    jobs: list[NormalizedJob] = []
    seen_ids: set[int] = set()

    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        csrf = client.get(f"{BASE_URL}/api/auth/csrf")
        csrf.raise_for_status()
        headers = {"x-csrf-token": csrf.json()["csrfToken"]}

        if department_filter is None:
            searches: list[tuple[int | None, str]] = [(None, "")]
        else:
            dept_response = client.get(
                f"{BASE_URL}/api/geo/{namespace}/postingattributes/departments/{namespace}/{job_board_id}/{CULTURE}"
            )
            dept_response.raise_for_status()
            searches = [
                (dept["attributeId"], dept["attributeValue"])
                for dept in dept_response.json()["postingAttributesAttributesList"]
                if department_filter(dept["attributeValue"])
            ]

        for department_id, department_name in searches:
            start = 0
            for _ in range(MAX_PAGES):
                body = {
                    "clientNamespace": namespace,
                    "jobBoardCode": board,
                    "cultureCode": CULTURE,
                    "distanceUnit": 0,
                    "paginationStart": start,
                }
                if department_id is not None:
                    body["departmentId"] = department_id
                response = client.post(search_url, json=body, headers=headers)
                response.raise_for_status()
                payload = response.json()
                postings = payload.get("jobPostings") or []
                for raw in postings:
                    if raw["jobPostingId"] in seen_ids:
                        continue
                    seen_ids.add(raw["jobPostingId"])
                    if not _in_country(raw, country_code):
                        continue
                    jobs.append(_normalize(raw, namespace, board, department_name))
                start += len(postings)
                if not postings or start >= payload.get("maxCount", 0):
                    break
            else:
                logger.warning("%s: department %r hit MAX_PAGES=%d", name, department_name, MAX_PAGES)

    logger.info("%s: fetched %d jobs across %d department searches", name, len(jobs), len(searches))
    return jobs


def _in_country(raw: dict, country_code: str) -> bool:
    locations = raw.get("postingLocations") or []
    return any(loc.get("isoCountryCode") == country_code for loc in locations)


def _normalize(raw: dict, namespace: str, board: str, department_name: str) -> NormalizedJob:
    locations = raw.get("postingLocations") or []
    location = "; ".join(
        dict.fromkeys(
            ", ".join(p for p in (loc.get("cityName"), loc.get("stateCode"), loc.get("isoCountryCode")) if p)
            or loc.get("formattedAddress", "")
            for loc in locations
        )
    )
    if raw.get("hasVirtualLocation"):
        location = f"{location} (Remote)" if location else "Remote"
    posted = raw.get("postingStartTimestampUTC")
    return {
        "external_id": str(raw["jobPostingId"]),
        "title": raw["jobTitle"].strip(),
        "url": f"{BASE_URL}/{CULTURE}/{namespace}/{board}/jobs/{raw['jobPostingId']}",
        "location": location,
        "category": department_name,
        "posted_date": posted[:10] if posted else None,
        "platform": "Dayforce",
    }
