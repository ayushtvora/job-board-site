"""Dev Information Technology Ltd. (DEV IT) careers scraper (Canada).

devitpl.com/careers is a WordPress page that server-renders every opening
as a `.job-card` (`h4.job-title`, `.job-location`, positions, experience
and skills). All of them share one generic "Apply Now" form, and nothing
carries a job ID or posted date.

- DEV IT is Ahmedabad-based with an office in Ontario. On 2026-10-02 all
  12 openings were in Ahmedabad, so an empty result is expected until a
  Canadian opening is listed. Canada is matched on the card's location
  with CANADA_PATTERN; every opening is kept (it's an IT company and its
  openings are almost all technical).
- **No source job ID**, so external_id is a hash of title + location
  (first 16 hex chars of SHA-1). It's deterministic across runs, as
  CLAUDE.md requires, and a retitled or moved posting becomes a new row,
  which is the right outcome for a listing with no other identity.
- Every job links to the careers page itself, since there's no per-job page.
"""

import hashlib
import logging

import httpx
from bs4 import BeautifulSoup

from .base import CANADA_PATTERN, NormalizedJob

logger = logging.getLogger(__name__)

CAREERS_URL = "https://devitpl.com/careers/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"}


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        response = client.get(CAREERS_URL)
        response.raise_for_status()

    cards = BeautifulSoup(response.text, "html.parser").select(".job-card")
    if not cards:
        raise RuntimeError("DEV IT careers page has no .job-card elements; the layout may have changed")
    jobs: dict[str, NormalizedJob] = {}
    for card in cards:
        title_el = card.select_one(".job-title")
        location_el = card.select_one(".job-location")
        if title_el is None:
            continue
        title = title_el.get_text(" ", strip=True)
        location = location_el.get_text(" ", strip=True) if location_el else ""
        if not CANADA_PATTERN.search(location):
            continue
        job_id = hashlib.sha1(f"{title}|{location}".lower().encode()).hexdigest()[:16]
        jobs[job_id] = {
            "external_id": job_id,
            "title": title,
            "url": CAREERS_URL,
            "location": location,
            "category": "",
            "posted_date": None,
            "platform": "DEV IT careers page (custom)",
        }

    logger.info("DEV IT: fetched %d Canadian jobs (of %d openings)", len(jobs), len(cards))
    return list(jobs.values())
