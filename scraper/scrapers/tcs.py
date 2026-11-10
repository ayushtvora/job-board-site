"""Tata Consultancy Services (TCS) careers scraper, scoped to Canada + technology roles.

TCS's own careers portal, iBegin, at `ibegin.tcsapps.com/candidate/next/`
(an Angular app; the URL came from the user, 2026-11-10). www.tcs.com is
Akamai-blocked even to headless Chromium, and the old `ibegin.tcs.com` no
longer resolves, but tcsapps.com isn't behind that WAF. The API was found
with a Playwright network capture; plain httpx works.

- `POST /api/<locale>/search/jobs` with
  `{"includeRegularJob", "includeWalkIn", "searchTerms", "jobLocationFilters",
  "jobDomainFilters", "experienceLevelFilters", "skillFilters",
  "relevancySortOrder", "recentSortOrder", "lastDateToApplySortOrder",
  "page", "resultsPerPage"}` → a Spring page (`content[]`, `totalPages`,
  `last`). `page` is 1-based; `resultsPerPage` must be 10, 25 or 50.
- **The locale is the country filter**: `en-CA` returns only Canadian
  postings (161 on 2026-11-10: Toronto, Mississauga, Montreal, Calgary, ...).
- **Request requirements**: an `XSRF-TOKEN` cookie (set by any `GET /api/...`,
  e.g. `/api/candidate`) echoed back as a `next-xsrf-token` header, plus
  `Origin` and `Referer` headers. Without Origin/Referer every API call,
  including the job detail GET, is a 403.
- Per job: `id` (e.g. "438870J", the stable ID, used as external_id),
  `title`, `location` ("Toronto, ON"; Quebec is "PQ"), `domain` (the job
  function), `minimum/maximumExperienceInYears`, `applyBy` (application
  deadline), `skills[]`, `walkIn`. **No posted date** anywhere, including
  the detail endpoint, so it falls back to first_seen_at.
- Scope: `domain` (the site's "Function" filter) in TECH_DOMAINS. All 161
  Canadian postings were "TECHNOLOGY" on 2026-11-10; the other domains are
  finance, HR, business process services and so on. Data titles are kept
  from any domain.
- Job page: `/candidate/next/<locale>/jobs/<id>`. The description is
  `GET /api/<locale>/job/desc/<id without the trailing "J">` (`payload.description`,
  HTML), fetched by scraper/descriptions.py's `fetch_tcs`.
"""

import logging

import httpx

from .base import NormalizedJob, is_data_title

logger = logging.getLogger(__name__)

ORIGIN = "https://ibegin.tcsapps.com"
BASE_URL = f"{ORIGIN}/candidate/next"
LOCALE = "en-CA"
PAGE_SIZE = 50
MAX_PAGES = 40
TECH_DOMAINS = {"TECHNOLOGY", "IT INFRASTRUCTURE SERVICES", "QUALITY ASSURANCE"}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": ORIGIN,
    "Referer": f"{BASE_URL}/{LOCALE}/jobs/search",
}


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    total = 0

    with httpx.Client(timeout=30, headers=HEADERS) as client:
        client.get(f"{BASE_URL}/api/candidate").raise_for_status()
        token = client.cookies.get("XSRF-TOKEN")
        if not token:
            raise RuntimeError("TCS iBegin didn't set an XSRF-TOKEN cookie")

        for page in range(1, MAX_PAGES + 1):
            response = client.post(
                f"{BASE_URL}/api/{LOCALE}/search/jobs",
                json={
                    "includeRegularJob": True,
                    "includeWalkIn": True,
                    "searchTerms": [],
                    "jobLocationFilters": [],
                    "jobDomainFilters": [],
                    "experienceLevelFilters": [],
                    "skillFilters": [],
                    "relevancySortOrder": None,
                    "recentSortOrder": "desc",
                    "lastDateToApplySortOrder": None,
                    "page": page,
                    "resultsPerPage": PAGE_SIZE,
                },
                headers={"next-xsrf-token": token},
            )
            response.raise_for_status()
            payload = response.json()["payload"]
            for raw in payload.get("content") or []:
                if raw["id"] in seen_ids:
                    continue
                seen_ids.add(raw["id"])
                total += 1
                if (raw.get("domain") or "").upper() in TECH_DOMAINS or is_data_title(raw["title"]):
                    jobs.append(_normalize(raw))
            if payload.get("last", True):
                break
        else:
            logger.warning("TCS scrape hit MAX_PAGES=%d without finishing", MAX_PAGES)

    logger.info("TCS: fetched %d matching jobs (of %d Canadian postings)", len(jobs), total)
    return jobs


def _normalize(raw: dict) -> NormalizedJob:
    domain = (raw.get("domain") or "").title()
    return {
        "external_id": raw["id"],
        "title": raw["title"].strip(),
        "url": f"{BASE_URL}/{LOCALE}/jobs/{raw['id']}",
        "location": raw.get("location") or "Canada",
        "category": domain,
        "posted_date": None,
        "platform": "TCS iBegin (custom, in-house)",
    }
