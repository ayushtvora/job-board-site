"""Shared helper for GC Jobs (the federal public service job site,
`emploisfp-psjobs.cfp-psc.gc.ca`), used by the Government of Canada,
Statistics Canada and National Research Council scrapers.

GC Jobs is an old server-rendered Java app with no API. Found by driving
its search page with Playwright and replaying the requests with httpx:

- `GET .../applicant/page2440?fromMenu=true&toggleLanguage=en` sets the
  session cookie. The results are a second request to the same page with
  `isSecondPartOfPage=1&isInitialNetworkCheck=1`, 20 per page.
- Later pages: `requestedPage=N&fromPage=N-1&tab=1&log=false&isSecondPartOfPage=1`
  in the same session. Paging continues until a page adds no new posters
  (406 postings over 21 pages on 2026-10-02).
- A keyword search (`title=`) works for page 1, but paging after it falls
  back to the unfiltered list, so the whole list is read and filtered here.
- Each `li.searchResult` has the title link (`page1800?poster=<id>`, id =
  external_id) and lines for the closing date, the organization, optional
  sub-organization lines starting with "- ", then the location(s). There's
  no posting date (only the closing date), so posted_date is None.
- Other federal bodies post here too, including the NRC, Statistics Canada
  and the Bank of Canada; the per-organization scrapers filter on that line.
"""

import logging
import re
from collections.abc import Callable

import httpx
from bs4 import BeautifulSoup

from .base import NormalizedJob

logger = logging.getLogger(__name__)

SEARCH_URL = "https://emploisfp-psjobs.cfp-psc.gc.ca/psrs-srfp/applicant/page2440"
POSTER_URL = "https://emploisfp-psjobs.cfp-psc.gc.ca/psrs-srfp/applicant/page1800?poster={id}&toggleLanguage=en"
MAX_PAGES = 60
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36",
    "Accept-Language": "en-CA,en",
}
POSTER_ID_RE = re.compile(r"poster=(\d+)")

# Federal tech roles, in English or French. Deliberately not bare "data" or
# "engineer": GC Jobs has many data-collection clerks and marine/aircraft
# engineers.
TECH_TITLE_PATTERN = re.compile(
    r"developer|d[ée]veloppeu|software|logiciel|programmer|programmeu|\bIT\b|\bTI\b|information technology|"
    r"technologies? de l.information|cyber|cloud|infonuagi|devops|data scien|data engineer|data analy|"
    r"database|base de donn|donn[ée]es|network (?:admin|analyst|engineer)|r[ée]seau|"
    r"systems? (?:admin|analyst|engineer)|machine learning|\bAI\b|\bIA\b|artificial intelligence|"
    r"intelligence artificielle|\bweb\b|\bD365\b|power platform",
    re.IGNORECASE,
)


def scrape_gcjobs(*, name: str, org_filter: Callable[[str], bool]) -> list[NormalizedJob]:
    """Every GC Jobs posting whose organization passes `org_filter` and
    whose title matches TECH_TITLE_PATTERN."""
    postings: dict[str, NormalizedJob] = {}

    with httpx.Client(timeout=60, headers=HEADERS, follow_redirects=True) as client:
        client.get(SEARCH_URL, params={"fromMenu": "true", "toggleLanguage": "en"}).raise_for_status()
        for page in range(1, MAX_PAGES + 1):
            if page == 1:
                params = {"fromMenu": "true", "toggleLanguage": "en", "isSecondPartOfPage": "1", "isInitialNetworkCheck": "1"}
            else:
                params = {"requestedPage": str(page), "fromPage": str(page - 1), "tab": "1", "log": "false", "isSecondPartOfPage": "1"}
            response = client.get(SEARCH_URL, params=params)
            response.raise_for_status()
            new_on_page = 0
            for item in BeautifulSoup(response.text, "html.parser").select("li.searchResult"):
                job = _parse(item)
                if job is not None and job["external_id"] not in postings:
                    postings[job["external_id"]] = job
                    new_on_page += 1
            if new_on_page == 0:
                break
        else:
            logger.warning("%s scrape hit MAX_PAGES=%d without finishing", name, MAX_PAGES)

    if not postings:
        raise RuntimeError("GC Jobs returned no postings at all; the page layout may have changed")
    jobs = [job for job in postings.values() if org_filter(job["category"]) and TECH_TITLE_PATTERN.search(job["title"])]
    logger.info("%s: fetched %d matching jobs (of %d GC Jobs postings)", name, len(jobs), len(postings))
    return jobs


def _parse(item) -> NormalizedJob | None:
    link = item.select_one('a[href*="page1800"]')
    match = POSTER_ID_RE.search(link["href"]) if link else None
    if not match:
        return None
    cell = item.select_one(".tableCell")
    lines = [line.strip() for line in cell.get_text("\n").split("\n") if line.strip()] if cell else []
    # lines: "Closing date: ...", organization, "- sub-organization"..., location(s)
    organization = lines[1] if len(lines) > 1 else ""
    rest = [line for line in lines[2:] if not line.startswith("-")]
    return {
        "external_id": match.group(1),
        "title": link.get_text(strip=True),
        "url": POSTER_URL.format(id=match.group(1)),
        "location": rest[0] if rest else "",
        "category": organization,
        "posted_date": None,
        "platform": "GC Jobs",
    }
