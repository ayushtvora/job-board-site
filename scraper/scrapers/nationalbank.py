"""National Bank of Canada careers scraper, scoped to technology/data areas of interest.

National Bank's careers site (`emplois.bnc.ca`) runs on **Avature**, same
ATS as EA (scrapers/ea.py) — plain server-rendered HTML, parsed with
BeautifulSoup, no session needed (just a browser User-Agent).

- The "Additional area(s) of interest" filter is Avature dataset field
  `6472`, whose option IDs come from an autocomplete datasource
  (`_wizardPortalDatasetSingleColumnOptionsSearchApi`, whose request body
  carries per-session encrypted field IDs — not replayable headlessly).
  Found the IDs by driving the real field once with Playwright (2026-09-25),
  same technique as EA's investigation: 25044 = "Information technology",
  25045 = "Artificial intelligence (AI)", 25047 = "Web and digital",
  25059 = "Business intelligence and data". Unlike the datasource itself,
  the resulting listing URL is a plain GET:
  `SearchJobs/?6472[]=25044&6472[]=...&listFilterMode=1` (51 jobs with all
  four; 34 with IT alone).
- No country filter needed — National Bank's postings are Canadian (the
  unfiltered search's locations are all Canadian cities).
- **Pagination**: `jobOffset` in steps of 20, same as EA.
- Listing rows (`table#openPositionsList`) give title + detail link +
  location; the numeric job number is the detail URL's last path segment
  (also shown as "Job number" on the detail page) — used as `external_id`.
- **Posted date + category come from each job's detail page** ("Posting
  date" like `21-Aug-2026`, "Area(s) of interest"). The `SearchJobs/feed/`
  RSS has `pubDate` but is capped at 20 items regardless of paging — same
  limitation as EA's feed — so the detail page is the complete source.
  ~50 extra requests per daily run.
- `platform` = `"Avature"`.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from .base import NormalizedJob

logger = logging.getLogger(__name__)

SEARCH_URL = "https://emplois.bnc.ca/en_CA/careers/SearchJobs/"
AREA_FIELD = "6472[]"
AREA_IDS = ["25044", "25045", "25047", "25059"]
PAGE_SIZE = 20
MAX_PAGES = 30
# Detail pages fetched at once (one per posting, for its date and category).
DETAIL_WORKERS = 4
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}


def scrape() -> list[NormalizedJob]:
    listings: list[tuple[str, str, str, str]] = []
    seen_ids: set[str] = set()

    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        for page in range(MAX_PAGES):
            params = [(AREA_FIELD, area_id) for area_id in AREA_IDS]
            params += [("listFilterMode", "1"), ("jobOffset", str(page * PAGE_SIZE))]
            response = client.get(SEARCH_URL, params=params)
            response.raise_for_status()
            rows = BeautifulSoup(response.text, "html.parser").select("#openPositionsList tbody tr")
            if not rows:
                break

            for row in rows:
                link = row.select_one('a[data-map="job-detail-link"]')
                if link is None:
                    continue
                url = link["href"]
                job_id = url.rstrip("/").rsplit("/", 1)[-1]
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                cells = row.find_all("td")
                location = cells[0].get_text(" ", strip=True) if cells else ""
                listings.append((job_id, link.get_text(strip=True), url, location))
        else:
            logger.warning("National Bank scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(listings))

    # map() re-raises the first failed detail fetch, so a failure still fails
    # the whole scrape rather than returning a partial job list.
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as pool:
        jobs = list(pool.map(lambda listing: _normalize(*listing), listings))

    logger.info("National Bank: fetched %d jobs", len(jobs))
    return jobs


def _normalize(job_id: str, title: str, url: str, location: str) -> NormalizedJob:
    fields = _detail_fields(url)
    return {
        "external_id": job_id,
        "title": title,
        "url": url,
        "location": location or fields.get("Location(s)", ""),
        "category": fields.get("Area(s) of interest", ""),
        "posted_date": _parse_date(fields.get("Posting date")),
        "platform": "Avature",
    }


def _detail_fields(url: str) -> dict[str, str]:
    """Label -> value for the detail page's fields. Avature renders them two
    ways: a label div + value div ("Posting date"), or a single value div
    starting with a bold "Label:" ("Area(s) of interest: ...").

    Each fetch uses a fresh client, i.e. its own session: the site answers
    one request per session cookie at a time (confirmed 2026-10-02: 4
    parallel detail fetches took ~6s on one session, ~2.4s on four)."""
    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        response = client.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    fields: dict[str, str] = {}
    for field in soup.select(".article__content__view__field"):
        label = field.select_one(".article__content__view__field__label")
        value = field.select_one(".article__content__view__field__value")
        if label and value:
            fields[label.get_text(strip=True)] = value.get_text(" ", strip=True)
    for strong in soup.select(".article__content__view__field__value strong"):
        label = strong.get_text(strip=True).rstrip(":")
        value = strong.parent.get_text(" ", strip=True)[len(strong.get_text(strip=True)):].strip()
        fields.setdefault(label, value)
    return fields


def _parse_date(text: str | None) -> str | None:
    if not text:
        return None
    try:
        return datetime.strptime(text.strip(), "%d-%b-%Y").strftime("%Y-%m-%d")
    except ValueError:
        logger.warning("National Bank: unparseable posting date %r", text)
        return None
