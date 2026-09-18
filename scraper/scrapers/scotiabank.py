"""Scotiabank careers scraper (IT & Digital Banking Jobs category).

Runs on SAP SuccessFactors (Jobs2Web career site layer) — a fourth distinct
ATS (RBC/BMO use Phenom, SOTI/CIBC/TD use Workday, EA uses Avature). Plain
server-rendered HTML table, no session/JS required, parsed with
BeautifulSoup.

- The given URL (`/go/IT-&-Digital-Banking-Jobs/2298017/`) *is* the
  "Technology" filter — it's a category-specific landing page, not a
  generic search with query-string facets like the other scrapers. Only
  filter requested for Scotiabank is "Technology", with no country facet
  applied on top (unlike BMO/CIBC/TD), so this scrapes that page as-is,
  whatever countries it includes.
- **Pagination** is a URL path segment (not a query param), in steps of the
  page size (25): `.../2298017/0/`, `.../2298017/25/`, `.../2298017/50/`,
  etc. — confirmed `/0/` is equivalent to the bare category URL (both give
  "Page 1 of N"), so the loop can always include the offset uniformly.
- **Fields available per row**: title + detail URL (`.jobTitle-link`,
  numeric job ID as the URL's trailing path segment), a human-readable
  date (`.jobDate`, e.g. "Sep 18, 2026"), and location (`.jobLocation`,
  e.g. "Toronto, ON, CA, M5H1H1").
- No per-job category is shown (the whole page is already one category), so
  `category` is hardcoded to this page's own label, same reasoning as the
  Workday scrapers' category facet.
- **`platform` = `"SuccessFactors"`** for Scotiabank.
"""

import logging
import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://jobs.scotiabank.com"
CATEGORY_PATH = "/go/IT-%26-Digital-Banking-Jobs/2298017"
CATEGORY_LABEL = "IT & Digital Banking Jobs"

PAGE_SIZE = 25
MAX_PAGES = 50  # safety cap; this category currently has ~288 jobs

ROLE_ID_RE = re.compile(r"/(\d+)/$")
RESULTS_COUNT_RE = re.compile(r"Results \d+ to \d+ of (\d+)")


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    offset = 0
    total: int | None = None

    with httpx.Client(timeout=30) as client:
        for _ in range(MAX_PAGES):
            url = f"{BASE_URL}{CATEGORY_PATH}/{offset}/"
            response = client.get(url, params={"q": "", "sortColumn": "referencedate", "sortDirection": "desc"})
            response.raise_for_status()

            if total is None:
                match = RESULTS_COUNT_RE.search(response.text)
                total = int(match.group(1)) if match else 0

            page_jobs = _parse_listing(response.text)
            if not page_jobs:
                break

            for job in page_jobs:
                if job["external_id"] in seen_ids:
                    continue
                seen_ids.add(job["external_id"])
                jobs.append(job)

            offset += PAGE_SIZE
            if offset >= total:
                break
        else:
            logger.warning("Scotiabank scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Scotiabank: fetched %d jobs (site reported total=%s)", len(jobs), total)
    return jobs


def _parse_listing(html: str) -> list[NormalizedJob]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[NormalizedJob] = []

    for row in soup.select("tr.data-row"):
        link = row.select_one("td.colTitle a.jobTitle-link")
        date_el = row.select_one("td.colDate .jobDate")
        location_el = row.select_one("td.colLocation .jobLocation")
        if link is None:
            continue

        href = link["href"]
        match = ROLE_ID_RE.search(href)
        if not match:
            continue

        jobs.append(
            {
                "external_id": match.group(1),
                "title": link.get_text(strip=True),
                "url": f"{BASE_URL}{href}",
                "location": location_el.get_text(strip=True) if location_el else "",
                "category": CATEGORY_LABEL,
                "posted_date": _parse_date(date_el.get_text(strip=True)) if date_el else None,
                "platform": "SuccessFactors",
            }
        )

    return jobs


def _parse_date(text: str) -> str | None:
    try:
        return datetime.strptime(text, "%b %d, %Y").date().isoformat()
    except ValueError:
        return None
