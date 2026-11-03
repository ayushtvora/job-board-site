"""Government of British Columbia (BC Public Service) careers scraper (IT jobs).

gov.bc.ca's "current job postings" link to the BC Public Service's
hrsmart/Talent Management site, which server-renders every posting in one
table: `GET https://bcpublicservice.hua.hrsmart.com/hr/ats/JobSearch/viewAll/jobSearchPaginationExternal_pageSize:100/jobSearchPaginationExternal_page:N`.

- Columns: ministry/organization, req # (external_id), job title (link to
  `/hr/ats/Posting/view/<req>`), union, work options, location, date
  opened (M/D/YYYY, posted_date), close date. 73 postings on 2026-10-02,
  all in BC.
- Titles start with the BC classification code ("CLK 12R - Dispatcher",
  "ISL 27R - Senior Database Administrator"). "IS" and "ISL" are the
  Information Systems classifications, which is the tech scope here; other
  titles are kept only if they name a tech role (managers are classified
  "Band N", so "Band 3 - Manager, IT Security" is caught this way).
- Pagination: pages of 100 until a page adds no new req numbers.
"""

import logging
import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from .base import NormalizedJob, is_data_title

logger = logging.getLogger(__name__)

BASE_URL = "https://bcpublicservice.hua.hrsmart.com"
LIST_URL = BASE_URL + "/hr/ats/JobSearch/viewAll/jobSearchPaginationExternal_pageSize:100/jobSearchPaginationExternal_page:{page}"
MAX_PAGES = 20
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"}
IS_CLASSIFICATION_RE = re.compile(r"^ISL?\s+\d")
TECH_TITLE_PATTERN = re.compile(
    r"developer|software|programmer|\bIT\b|information technology|information systems|cyber|cloud|devops|"
    r"data scien|data engineer|data analy|database|network|systems? (?:admin|analyst|engineer)|"
    r"machine learning|\bAI\b|artificial intelligence|digital|web",
    re.IGNORECASE,
)


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen: set[str] = set()

    with httpx.Client(timeout=60, headers=HEADERS, follow_redirects=True) as client:
        for page in range(1, MAX_PAGES + 1):
            response = client.get(LIST_URL.format(page=page))
            response.raise_for_status()
            new_on_page = 0
            for row in BeautifulSoup(response.text, "html.parser").select("tr"):
                cells = row.select("td")
                if len(cells) < 8:
                    continue
                req = cells[1].get_text(strip=True)
                if req in seen:
                    continue
                seen.add(req)
                new_on_page += 1
                title = cells[2].get_text(" ", strip=True)
                if IS_CLASSIFICATION_RE.match(title) or TECH_TITLE_PATTERN.search(title) or is_data_title(title):
                    jobs.append(_normalize(cells, req, title))
            if new_on_page == 0:
                break
        else:
            logger.warning("Government of BC scrape hit MAX_PAGES=%d without finishing", MAX_PAGES)

    if not seen:
        raise RuntimeError("BC Public Service listing returned no postings; the page layout may have changed")
    logger.info("Government of BC: fetched %d matching jobs (of %d postings)", len(jobs), len(seen))
    return jobs


def _normalize(cells, req: str, title: str) -> NormalizedJob:
    link = cells[2].select_one("a")
    href = link["href"] if link else f"/hr/ats/Posting/view/{req}"
    return {
        "external_id": req,
        "title": title,
        "url": href if href.startswith("http") else f"{BASE_URL}{href}",
        "location": cells[5].get_text(" ", strip=True),
        "category": cells[0].get_text(strip=True),
        "posted_date": _parse_date(cells[6].get_text(strip=True)),
        "platform": "hrsmart",
    }


def _parse_date(text: str) -> str | None:
    try:
        return datetime.strptime(text, "%m/%d/%Y").date().isoformat()
    except ValueError:
        return None
