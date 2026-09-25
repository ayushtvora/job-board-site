"""SAP careers scraper (Canada / Software-Design and Development jobs).

Runs on SAP's self-hosted **SAP SuccessFactors** career site (jobs.sap.com) —
same ATS family as scrapers/scotiabank.py, but an older/different layer:
classic server-rendered SuccessFactors search (`/search/`) rather than
Scotiabank's simpler static category landing page. See CLAUDE.md's "SAP
scraping approach" section for how this was found.

- **Requires a normal browser User-Agent header** — a bare request with no UA
  gets blocked; a Chrome-like UA string is sufficient (confirmed live, no
  further challenge/cookie dance needed — a basic UA check, not a WAF).
- List URL: `GET /search/?q=&locationsearch=Canada` — confirmed filters to
  Canada jobs only (page title becomes "Canada - SAP Jobs").
- **No working category/department facet via plain HTTP** — the dropdown in
  the HTML is populated client-side; can't filter server-side by category.
  Every Canada job is fetched and then filtered client-side (see below).
- Pagination: `startrow=N` query param, page size 25.
- List view only has title, job detail URL (which embeds a stable numeric
  requisition ID as its trailing path segment, e.g. `1426752233`), and a
  free-text location string. No category, no posted date at the list level.
- **Category ("Work Area") and posted date are only on the detail page**
  (`https://jobs.sap.com/job/<slug>/<id>/`) — one extra GET per job per run,
  same two-tier pattern as scrapers/soti.py. Confirmed selectors:
  `span[data-careersite-propertyid="department"]` for Work Area (e.g.
  "Software-Development Operations"; the requested category label
  "Software-Design and Development" is also a real observed value on this
  site) and `span[data-careersite-propertyid="date"]` for Posted Date (a
  plain "Mon D, YYYY" string, same format as Scotiabank's `.jobDate`).
- Since there's no server-side category filter, jobs are filtered
  client-side to Work Area containing "software-design and development"
  (case-insensitive) after fetching each detail page.
- `platform` = `"SuccessFactors"`.
"""

import logging
import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://jobs.sap.com"
SEARCH_PATH = "/search/"
CATEGORY_LABEL_FILTER = "software-design and development"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

PAGE_SIZE = 25
MAX_PAGES = 20  # safety cap; this Canada-wide search currently has ~17 jobs

JOB_ID_RE = re.compile(r"/(\d+)/?$")
TOTAL_RE = re.compile(r"of\s+(\d+)", re.IGNORECASE)


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    startrow = 0
    total: int | None = None

    with httpx.Client(timeout=30, headers=HEADERS) as client:
        for _ in range(MAX_PAGES):
            response = client.get(
                f"{BASE_URL}{SEARCH_PATH}",
                params={"q": "", "locationsearch": "Canada", "startrow": startrow},
            )
            response.raise_for_status()

            if total is None:
                total = _parse_total(response.text)

            page_jobs = _parse_listing(response.text)
            if not page_jobs:
                break

            for job in page_jobs:
                if job["external_id"] in seen_ids:
                    continue
                seen_ids.add(job["external_id"])
                jobs.append(job)

            startrow += PAGE_SIZE
            if total is not None and startrow >= total:
                break
        else:
            logger.warning("SAP scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("SAP: fetched %d Canada jobs (site reported total=%s)", len(jobs), total)

    filtered: list[NormalizedJob] = []
    with httpx.Client(timeout=30, headers=HEADERS) as client:
        for job in jobs:
            detail = _fetch_detail(client, job["url"])
            if detail is None:
                continue
            work_area, posted_date = detail
            if CATEGORY_LABEL_FILTER not in work_area.lower():
                continue
            job["category"] = work_area
            job["posted_date"] = posted_date
            filtered.append(job)

    logger.info(
        "SAP: %d of %d Canada jobs matched Work Area containing %r",
        len(filtered),
        len(jobs),
        CATEGORY_LABEL_FILTER,
    )
    return filtered


def _parse_total(html: str) -> int | None:
    soup = BeautifulSoup(html, "html.parser")
    label = soup.select_one(".paginationLabel")
    if label is None:
        return None
    match = TOTAL_RE.search(label.get_text())
    return int(match.group(1)) if match else None


def _parse_listing(html: str) -> list[NormalizedJob]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[NormalizedJob] = []

    for row in soup.select("tr.data-row"):
        link = row.select_one("td.colTitle a.jobTitle-link")
        location_el = row.select_one("td.colLocation .jobLocation")
        if link is None:
            continue

        href = link["href"]
        match = JOB_ID_RE.search(href)
        if not match:
            continue

        jobs.append(
            {
                "external_id": match.group(1),
                "title": link.get_text(strip=True),
                "url": f"{BASE_URL}{href}",
                "location": location_el.get_text(strip=True) if location_el else "",
                "category": "",  # filled in from the detail page below
                "posted_date": None,  # filled in from the detail page below
                "platform": "SuccessFactors",
            }
        )

    return jobs


def _fetch_detail(client: httpx.Client, url: str) -> tuple[str, str | None] | None:
    response = client.get(url)
    if response.status_code != 200:
        logger.warning("SAP: detail fetch failed for %s (status %d)", url, response.status_code)
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    work_area_el = soup.select_one('span[data-careersite-propertyid="department"]')
    date_el = soup.select_one('span[data-careersite-propertyid="date"]')

    work_area = work_area_el.get_text(strip=True) if work_area_el else ""
    posted_date = _parse_date(date_el.get_text(strip=True)) if date_el else None
    return work_area, posted_date


def _parse_date(text: str) -> str | None:
    try:
        return datetime.strptime(text, "%b %d, %Y").date().isoformat()
    except ValueError:
        return None
