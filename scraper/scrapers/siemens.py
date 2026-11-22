"""Siemens careers scraper (Canada, tech and data roles).

jobs.siemens.com is Avature, server-rendered, so plain httpx is enough.
Investigated 2026-11-22.

- Country is field `42386`, Canada = `812214` (an AJAX-only option ID,
  found with Playwright): 97 postings.
- **Paging is `folderOffset`**, fixed at 6 per page (`folderRecordsPerPage`
  is ignored). `jobOffset`, EA's param, is silently ignored and repeats
  page 1. A short read raises, so it can't delete the missed jobs' rows.
- Scope is the listing's job family (Research & Development, Information
  Technology, Cybersecurity) plus core titles. "Engineering" is left out:
  here it's field technicians and building-systems project managers.
- The listing shows only "Multiple Locations" and has no date, so each kept
  job's detail page gives the locations, posted date and description.
- The country filter also returns "Any Siemens location in the world"
  postings of foreign subsidiaries (Siemens K.K., Siemens Brasil). Those
  have no location list and are kept only for a Canadian Siemens company.
"""

import logging
import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from .base import NormalizedJob, clean_description, is_core_title

logger = logging.getLogger(__name__)

SEARCH_URL = "https://jobs.siemens.com/en_US/externaljobs/SearchJobs/"
FILTER_PARAMS = {"42386": "812214", "listFilterMode": "1"}  # Country = Canada
JOB_FAMILIES = {"Research & Development", "Information Technology", "Cybersecurity"}
PAGE_SIZE = 6
MAX_PAGES = 100
MIN_COMPLETE = 0.95
TOTAL_RE = re.compile(r"(\d+) results")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"}


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        listings = _fetch_listings(client)
        jobs = []
        for job_id, (title, url, family) in listings.items():
            if family not in JOB_FAMILIES and not is_core_title(title):
                continue
            response = client.get(url)
            response.raise_for_status()
            job = _normalize(job_id, title, url, family, response.text)
            if job:
                jobs.append(job)

    logger.info("Siemens: fetched %d jobs (of %d in Canada)", len(jobs), len(listings))
    return jobs


def _fetch_listings(client: httpx.Client) -> dict[str, tuple[str, str, str]]:
    """Every Canadian posting as id -> (title, url, job family)."""
    listings: dict[str, tuple[str, str, str]] = {}
    total = None
    for page in range(MAX_PAGES):
        response = client.get(SEARCH_URL, params={**FILTER_PARAMS, "folderOffset": page * PAGE_SIZE})
        response.raise_for_status()
        if total is None:
            match = TOTAL_RE.search(response.text)
            if match is None:
                raise RuntimeError("Siemens: no result count on the search page")
            total = int(match.group(1))
        articles = BeautifulSoup(response.text, "html.parser").select("article.article--result")
        for article in articles:
            link = article.select_one(".article__header__text__title a[href]")
            if link is None:
                continue
            family = article.select_one(".list-item-family")
            listings[link["href"].rstrip("/").rsplit("/", 1)[-1]] = (
                link.get_text(" ", strip=True),
                link["href"],
                family.get_text(strip=True) if family else "",
            )
        if not articles or (page + 1) * PAGE_SIZE >= total:
            break

    if len(listings) < total * MIN_COMPLETE:
        raise RuntimeError(f"Siemens: read only {len(listings)} of {total} postings")
    return listings


def _normalize(job_id: str, title: str, url: str, family: str, html: str) -> NormalizedJob | None:
    soup = BeautifulSoup(html, "html.parser")
    fields = {}
    for field in soup.select(".article__content__view__field"):
        label = field.select_one(".article__content__view__field__label")
        value = field.select_one(".article__content__view__field__value")
        if label and value:
            fields[label.get_text(strip=True)] = value.get_text(" ", strip=True)
    if "Job ID" not in fields:
        raise RuntimeError(f"Siemens: job {job_id}'s page has no details")

    # Items read "Kitchener - Ontario - Canada", or "Ontario - Canada" under
    # "Any Siemens location in".
    items = [li.get_text(" ", strip=True) for li in soup.select("ul.list--locations li")]
    if items:
        location = "; ".join(item.replace(" - ", ", ") for item in items if item.endswith("Canada"))
    else:
        location = "Canada" if "Canada" in fields.get("Company", "") else ""
    if not location:
        return None

    posted = fields.get("Posted since")
    # The first details block is the fields above; the posting follows it.
    body = soup.select("article.article--details")[1:]
    return {
        "external_id": job_id,
        "title": title,
        "url": url,
        "location": location,
        "category": family,
        "posted_date": datetime.strptime(posted, "%d-%b-%Y").date().isoformat() if posted else None,
        "platform": "Avature",
        "description": clean_description("".join(str(block) for block in body)),
    }
