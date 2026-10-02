"""NASA careers scraper (Canada).

NASA civil-service jobs are posted on USAJOBS. The site's own search page
calls a JSON endpoint that needs no API key (the documented
data.usajobs.gov API does): `POST https://www.usajobs.gov/Search/ExecuteSearch`
with `{"Organization": ["NN"], "Page": N}`, where "NN" is NASA's agency
code (15 open postings on 2026-10-02). `Location` in that body is ignored,
so Canada is matched client-side.

These are US federal jobs, almost all restricted to US citizens and
located at NASA centres, so an empty result is expected; this exists so
NASA is tracked like every other company on the list.

- Per job: `DocumentID` (external_id; the job page is
  `usajobs.gov/job/<DocumentID>`), `Title`, `LocationDisplay`, `Agency`
  (the NASA centre, used as category), `DateDisplay` ("Open 09/18/2026 to
  10/02/2026", whose first date is the posted date).
"""

import logging
import re
from datetime import datetime

import httpx

from .base import CANADA_PATTERN, NormalizedJob

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.usajobs.gov/Search/ExecuteSearch"
NASA_AGENCY_CODE = "NN"
MAX_PAGES = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36",
    "Accept": "application/json",
}
OPEN_DATE_RE = re.compile(r"Open (\d{2}/\d{2}/\d{4})")


def scrape() -> list[NormalizedJob]:
    postings: list[dict] = []
    with httpx.Client(timeout=30, headers=HEADERS) as client:
        for page in range(1, MAX_PAGES + 1):
            response = client.post(SEARCH_URL, json={"Organization": [NASA_AGENCY_CODE], "Page": page})
            response.raise_for_status()
            payload = response.json()
            postings.extend(payload.get("Jobs") or [])
            if not (payload.get("Pager") or {}).get("HasNextPage"):
                break

    jobs = [_normalize(raw) for raw in postings if CANADA_PATTERN.search(raw.get("LocationDisplay") or "")]
    logger.info("NASA: fetched %d Canadian jobs (of %d NASA postings)", len(jobs), len(postings))
    return jobs


def _normalize(raw: dict) -> NormalizedJob:
    match = OPEN_DATE_RE.search(raw.get("DateDisplay") or "")
    return {
        "external_id": str(raw["DocumentID"]),
        "title": raw["Title"].strip(),
        "url": f"https://www.usajobs.gov/job/{raw['DocumentID']}",
        "location": raw.get("LocationDisplay") or "",
        "category": raw.get("Agency") or "",
        "posted_date": datetime.strptime(match.group(1), "%m/%d/%Y").date().isoformat() if match else None,
        "platform": "USAJOBS",
    }
