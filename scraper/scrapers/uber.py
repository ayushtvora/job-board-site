"""Uber careers scraper (Canada / engineering, science and data teams).

Unblocked 2026-10-02. The 2026-09-19 investigation hit an app-level CSRF
gate on careers.uber.com's `loadSearchJobsResults` RPC. Uber has since moved
its careers site to `jobs.uber.com` (a Next.js app; the old pages redirect
there), whose search is a plain GET:
`https://jobs.uber.com/api/jobs/search/?page=N&pagesize=100` (found with a
Playwright network capture).

- **Needs a real browser**, like scrapers/meta.py. Cloudflare answers 403
  to Python's httpx (HTTP/1.1 and HTTP/2 alike, with browser headers), a
  client-fingerprint block, while curl and Chromium get through. Headless
  Chromium's default user agent ("HeadlessChrome") is also blocked, so a
  normal Chrome UA is set. The scraper loads `/en/jobs/` once, then calls
  the API with `fetch()` from inside the page.
- `pagesize` (lowercase; `pageSize` is ignored) goes up to 100, so the
  whole list (578 jobs on 2026-10-02) is 6 requests. `location=` only
  matches exact city names, so Canada is filtered client-side on
  `Locations[].Country`. That was 14 jobs in Toronto/Montreal on
  2026-10-02, all sales, so an empty result is expected for now.
- Scope is the `Teams` field: Engineer, Science, Data, Technical Security,
  System Operations.
- Per job: `Id` (external_id), `Title`, `Locations[]` (City/Region/Country),
  `Teams[]`, `DisplayDate` (ISO datetime), `Urls[0].Url` (relative job page).
"""

import json
import logging

from playwright.sync_api import sync_playwright

from .base import BROWSER_LOCK, NormalizedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://jobs.uber.com"
PAGE_SIZE = 100
MAX_PAGES = 30
TEAMS = {"Engineer", "Science", "Data", "Technical Security", "System Operations"}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
NAV_TIMEOUT_MS = 45_000
FETCH_JS = """async (query) => {
    const response = await fetch('/api/jobs/search/?' + query, {headers: {Accept: 'application/json'}});
    return [response.status, await response.text()];
}"""


def scrape() -> list[NormalizedJob]:
    postings: list[dict] = []
    with BROWSER_LOCK, sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(f"{BASE_URL}/en/jobs/", wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            for page_number in range(1, MAX_PAGES + 1):
                status, body = page.evaluate(FETCH_JS, f"page={page_number}&pagesize={PAGE_SIZE}")
                if status != 200:
                    raise ValueError(f"Uber job search returned HTTP {status}")
                payload = json.loads(body)
                postings.extend(payload.get("jobs") or [])
                if page_number >= (payload.get("totalPages") or 0):
                    break
            else:
                logger.warning("Uber scrape hit MAX_PAGES=%d without finishing", MAX_PAGES)
        finally:
            browser.close()

    jobs = [_normalize(raw) for raw in postings if _is_canada(raw) and TEAMS.intersection(raw.get("Teams") or [])]
    logger.info("Uber: fetched %d matching jobs (of %d postings)", len(jobs), len(postings))
    return jobs


def _canadian_locations(raw: dict) -> list[dict]:
    return [loc for loc in raw.get("Locations") or [] if (loc.get("Country") or "") == "Canada"]


def _is_canada(raw: dict) -> bool:
    return bool(_canadian_locations(raw))


def _normalize(raw: dict) -> NormalizedJob:
    places = [", ".join(p for p in (loc.get("City"), loc.get("Region")) if p) for loc in _canadian_locations(raw)]
    urls = raw.get("Urls") or []
    path = urls[0]["Url"] if urls else f"/en/jobs/{raw['Id']}/"
    posted = raw.get("DisplayDate")
    return {
        "external_id": str(raw["Id"]),
        "title": raw["Title"].strip(),
        "url": f"{BASE_URL}{path}",
        "location": "; ".join(dict.fromkeys(places)),
        "category": ", ".join(raw.get("Teams") or []),
        "posted_date": posted[:10] if posted else None,
        "platform": "Uber Careers (custom, in-house)",
    }
