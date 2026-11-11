"""Two Sigma careers scraper (Canada / Engineering and Quantitative Research).

careers.twosigma.com is Avature (same platform as EA and National Bank).
Its filter fields (`5084`-`5088`) have AJAX-only option IDs like EA's, but
the whole open-roles list is small (55 postings on 2026-10-02), so this
pages through the unfiltered `/careers/OpenRoles` listing and filters
client-side instead.

- Plain server-rendered HTML, `jobOffset` in steps of 10. Past the last
  page it serves an empty list.
- Per `article.article--result`: title link (`/careers/JobDetail/<slug>/<id>`,
  trailing numeric ID = external_id), the location ("United States - NY
  New York"), then category ("Engineering", "Quantitative Research", ...)
  and level in the sub-text.
- Two Sigma has no Canadian office (every posting was in New York, London,
  Houston, Shanghai or Tokyo), so an empty result is expected. No posted
  date is shown.
"""

import logging
import re

import httpx
from bs4 import BeautifulSoup

from .base import CANADA_PATTERN, NormalizedJob, is_core_title

logger = logging.getLogger(__name__)

LIST_URL = "https://careers.twosigma.com/careers/OpenRoles"
PAGE_SIZE = 10
MAX_PAGES = 30
CATEGORIES = {"Engineering", "Quantitative Research", "Data", "Technology"}
JOB_ID_RE = re.compile(r"/(\d+)/?$")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"}


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()

    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        for page in range(MAX_PAGES):
            response = client.get(LIST_URL, params={"jobOffset": page * PAGE_SIZE})
            response.raise_for_status()
            articles = BeautifulSoup(response.text, "html.parser").select("article.article--result")
            new_on_page = 0
            for article in articles:
                job = _parse(article)
                if job is None or job["external_id"] in seen_ids:
                    continue
                seen_ids.add(job["external_id"])
                new_on_page += 1
                in_scope = job["category"] in CATEGORIES or is_core_title(job["title"])
                if in_scope and CANADA_PATTERN.search(job["location"]):
                    jobs.append(job)
            if new_on_page == 0:
                break
        else:
            logger.warning("Two Sigma scrape hit MAX_PAGES=%d without finishing", MAX_PAGES)

    logger.info("Two Sigma: fetched %d matching jobs (of %d listed)", len(jobs), len(seen_ids))
    return jobs


def _parse(article) -> NormalizedJob | None:
    link = article.select_one(".article__header__text__title a")
    match = JOB_ID_RE.search(link["href"]) if link else None
    if not match:
        return None
    location = article.select_one(".article__header__content__text > .paragraph_inner-span")
    sub_text = [s.get_text(strip=True) for s in article.select(".article__header__content__sub-text .paragraph_inner-span")]
    return {
        "external_id": match.group(1),
        "title": link.get_text(strip=True),
        "url": link["href"],
        "location": location.get_text(strip=True) if location else "",
        "category": sub_text[0] if sub_text else "",
        "posted_date": None,
        "platform": "Avature",
    }
