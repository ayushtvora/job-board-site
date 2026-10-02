"""KPMG US careers scraper (Canada / all practice areas).

kpmguscareers.com/job-search/ is a WordPress site that server-renders the
first 12 results of a search (`?location=<text>&keyword=<text>`), with the
result count in `span[data-action="count"]`. Each result is an
`a[href^="/jobdetail/?jobId=<id>"]` card with the practice area, title and
locations.

KPMG US is the US member firm; Canadian roles are posted by KPMG Canada on
its own site. `location=Canada` returned 0 results on 2026-10-02, so an
empty result is expected. Further pages load through JavaScript, and no
working page parameter was found (`pg`, `paged`, `page`, `offset` and
`/page/N/` all repeat page 1), so only the first 12 results are read and a
warning is logged if there are more.
"""

import logging
import re

import httpx
from bs4 import BeautifulSoup

from .base import CANADA_PATTERN, NormalizedJob

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.kpmguscareers.com/job-search/"
BASE_URL = "https://www.kpmguscareers.com"
JOB_ID_RE = re.compile(r"jobId=(\d+)")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"}


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        response = client.get(SEARCH_URL, params={"location": "Canada"})
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    count_el = soup.select_one('[data-action="count"]')
    total = int(count_el.get_text(strip=True) or 0) if count_el else 0
    jobs: dict[str, NormalizedJob] = {}
    for card in soup.select('.holder--postings a[href*="jobdetail"]'):
        job = _parse(card)
        if job and CANADA_PATTERN.search(job["location"]):
            jobs.setdefault(job["external_id"], job)
    if total > len(jobs):
        logger.warning("KPMG US: %d results for Canada but only the first page (%d) is read", total, len(jobs))

    logger.info("KPMG US: fetched %d jobs (site reported %d)", len(jobs), total)
    return list(jobs.values())


def _parse(card) -> NormalizedJob | None:
    match = JOB_ID_RE.search(card["href"])
    if not match:
        return None
    # The list view repeats each field for the grid and list layouts, so
    # take the distinct pieces in order: level, practice area, title, then
    # the location count or locations.
    parts = list(dict.fromkeys(card.get_text("|", strip=True).split("|")))
    title = parts[2] if len(parts) > 2 else card.get_text(strip=True)
    return {
        "external_id": match.group(1),
        "title": title,
        "url": f"{BASE_URL}{card['href']}",
        "location": parts[-1].strip() if len(parts) > 3 else "",
        "category": parts[1].strip() if len(parts) > 1 else "",
        "posted_date": None,
        "platform": "KPMG Careers (custom, in-house)",
    }
