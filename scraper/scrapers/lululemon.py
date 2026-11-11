"""lululemon careers scraper (Canada, tech and data titles via keyword search).

`careers.lululemon.com` is Avature (like EA and National Bank), with
mostly store jobs. Investigated 2026-11-10.

- Its filter fields (State/Province/City, Business Unit, Area of
  Interest) have AJAX-only option IDs, like EA's, so they aren't used.
  Instead the listing's free-text `search=` param (the site's keyword box)
  runs once per term in `SEARCH_TERMS`, and results are kept when the
  title passes `base.is_core_title` (or `TECH_TITLE_PATTERN`) and the
  location is Canadian. Results are sorted by relevance, so paging stops
  at the first page with no kept title.
- Listing: `/en_US/careers/SearchJobs/?search=<term>&listFilterMode=1&jobOffset=N`,
  10 per page (plain server-rendered HTML). Each `article.article--result`
  has the title link (`.../JobDetail/<slug>/<id>`; the trailing number is
  the external_id) and a location like "Canada . British Columbia .
  Vancouver" (head office is Vancouver).
- No posted date on the listing, so the date falls back to first_seen_at.
  The description is fetched later by descriptions.py.
"""

import logging
import re

import httpx
from bs4 import BeautifulSoup

from .base import CANADA_PATTERN, CORE_SEARCH_TERMS, NormalizedJob, is_core_title

logger = logging.getLogger(__name__)

LIST_URL = "https://careers.lululemon.com/en_US/careers/SearchJobs/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
}
SEARCH_TERMS = (*CORE_SEARCH_TERMS, "engineer", "technology")
# Tech titles that is_core_title leaves out (it skips bare "engineer").
TECH_TITLE_PATTERN = re.compile(
    r"(?:cyber|security|cloud|network|platform|systems|integration|automation|quality|solutions?) engineer|"
    r"engineering manager|technology manager|architect",
    re.IGNORECASE,
)
PAGE_SIZE = 10
MAX_PAGES = 20
JOB_ID_RE = re.compile(r"/JobDetail/[^/]+/(\d+)")


def scrape() -> list[NormalizedJob]:
    jobs: dict[str, NormalizedJob] = {}
    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        for term in SEARCH_TERMS:
            for page in range(MAX_PAGES):
                response = client.get(
                    LIST_URL, params={"search": term, "listFilterMode": "1", "jobOffset": page * PAGE_SIZE}
                )
                response.raise_for_status()
                items = _parse(response.text)
                if not items:
                    break
                kept_on_page = False
                for job in items:
                    if not (is_core_title(job["title"]) or TECH_TITLE_PATTERN.search(job["title"])):
                        continue
                    kept_on_page = True
                    if CANADA_PATTERN.search(job["location"]):
                        jobs.setdefault(job["external_id"], job)
                if not kept_on_page:
                    break
            else:
                logger.warning("lululemon search for %r hit MAX_PAGES=%d", term, MAX_PAGES)
    logger.info("lululemon: fetched %d jobs", len(jobs))
    return list(jobs.values())


def _parse(html: str) -> list[NormalizedJob]:
    items = []
    for article in BeautifulSoup(html, "html.parser").select("article.article--result"):
        link = article.select_one(".article__header__text__title a[href]")
        if link is None:
            continue
        match = JOB_ID_RE.search(link["href"])
        if match is None:
            continue
        subtitle = article.select_one(".article__header__text__subtitle")
        # "Canada . British Columbia . Vancouver" -> "Vancouver, British Columbia, Canada"
        parts = [p.strip() for p in (subtitle.get_text(" ", strip=True) if subtitle else "").split(" . ") if p.strip()]
        items.append(
            {
                "external_id": match.group(1),
                "title": link.get_text(" ", strip=True),
                "url": link["href"],
                "location": ", ".join(reversed(parts)),
                "category": "Keyword search",
                "posted_date": None,
                "platform": "Avature",
            }
        )
    return items
