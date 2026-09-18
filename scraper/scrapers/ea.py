"""EA careers scraper, scoped to Canada + Software Development.

EA's careers site runs on Avature. Unlike RBC/SOTI, job data isn't embedded
as a single JSON blob — this is a plain server-rendered HTML listing, parsed
with BeautifulSoup. See CLAUDE.md's "EA scraping approach" section for how
this was found.

- The filter form's "Country" and "Job Category" fields are Avature
  "dataset" fields: each option is an opaque numeric ID, discovered (via a
  real browser session, since they're populated by an autocomplete API,
  not present in the static HTML) by watching the request the filter form
  fires on submit. Confirmed `8171=10577` is Country=Canada and
  `4536=8301` is Job Category=Software Development.
- Listing URL takes those as query params, e.g.
  `?8171=[10577]&8171_format=5683&4536=[8301]&4536_format=3019&listFilterMode=1`.
  The `_format` values are fixed companions to each field, not something to
  vary. Pagination is via `jobOffset` (steps of the page's actual size, 20,
  regardless of what `jobRecordsPerPage` requests — the site appears to
  hard-cap the page size server-side).
- Each result card exposes: title + detail URL (`.article__header__text__title a`),
  primary location (`.list-item-location`), and the numeric role ID both in
  the URL's trailing path segment and in `.list-item-id` ("Role ID <n>") —
  used as `external_id`.
- No per-job category or posted date is rendered anywhere in the listing or
  detail page. Since this scraper's query is fixed to one category, category
  is hardcoded to that facet's label (as with SOTI). For posted date: EA
  also publishes an RSS feed (`Home/feed/`) that accepts the same filter
  params and includes an accurate `pubDate` — but it always returns only its
  20 most-recently-posted matches for the filter, ignoring
  `jobRecordsPerPage`/`jobOffset` entirely (confirmed by requesting several
  values and getting back the same 20 items every time). So it only covers
  the newest slice of a larger result set. Used as a best-effort lookup:
  jobs in that slice get an exact `posted_date`; older jobs fall back to
  `None`, per the posted-date-fallback rule in CLAUDE.md (the UI shows
  `first_seen_at` instead of a blank date).
- `platform` = `"Avature"` for EA.
"""

import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://jobs.ea.com"
LIST_URL = f"{BASE_URL}/en_US/careers/Home/"
FEED_URL = f"{BASE_URL}/en_US/careers/Home/feed/"

# Opaque Avature dataset field/value IDs, not derivable from their labels —
# confirmed by watching the filter form's own request (see module docstring).
FILTER_PARAMS = {
    "8171": "[10577]",  # Country = Canada
    "8171_format": "5683",
    "4536": "[8301]",  # Job Category = Software Development
    "4536_format": "3019",
    "listFilterMode": "1",
}
CATEGORY_LABEL = "Software Development"

PAGE_SIZE = 20  # the site's actual (unconfigurable) page size — see docstring
MAX_PAGES = 50  # safety cap; this filter currently has ~50 jobs

ROLE_ID_RE = re.compile(r"/(\d+)$")
RESULTS_COUNT_RE = re.compile(r'aria-label="(\d+) results"')


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=30) as client:
        posted_dates = _fetch_posted_dates(client)

        jobs: list[NormalizedJob] = []
        seen_ids: set[str] = set()
        offset = 0
        total: int | None = None

        for _ in range(MAX_PAGES):
            response = client.get(LIST_URL, params={**FILTER_PARAMS, "jobOffset": offset})
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
                job["posted_date"] = posted_dates.get(job["external_id"])
                jobs.append(job)

            offset += PAGE_SIZE
            if offset >= total:
                break
        else:
            logger.warning("EA scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("EA: fetched %d jobs (site reported total=%s)", len(jobs), total)
    return jobs


def _parse_listing(html: str) -> list[NormalizedJob]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[NormalizedJob] = []

    for article in soup.select("article.article--result"):
        link = article.select_one(".article__header__text__title a")
        if link is None:
            continue
        url = link["href"]
        match = ROLE_ID_RE.search(url)
        if not match:
            continue

        location_el = article.select_one(".list-item-location")
        jobs.append(
            {
                "external_id": match.group(1),
                "title": link.get_text(strip=True),
                "url": url,
                "location": location_el.get_text(strip=True) if location_el else "",
                "category": CATEGORY_LABEL,
                "posted_date": None,  # filled in by scrape() from the RSS lookup
                "platform": "Avature",
            }
        )

    return jobs


def _fetch_posted_dates(client: httpx.Client) -> dict[str, str]:
    """Best-effort external_id -> "YYYY-MM-DD" lookup from the RSS feed.

    Only covers the ~20 most recently posted jobs matching the filter (see
    module docstring) — callers should treat a miss as "date unknown", not
    an error.
    """
    response = client.get(FEED_URL, params=FILTER_PARAMS)
    response.raise_for_status()

    root = ElementTree.fromstring(response.text)
    dates: dict[str, str] = {}
    for item in root.iterfind(".//item"):
        link = item.findtext("link")
        pub_date = item.findtext("pubDate")
        if not link or not pub_date:
            continue
        match = ROLE_ID_RE.search(link.strip())
        if not match:
            continue
        parsed: datetime = parsedate_to_datetime(pub_date.strip())
        dates[match.group(1)] = parsed.date().isoformat()

    return dates
