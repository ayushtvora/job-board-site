"""Google careers scraper (Canada / free-text "Software Engineer" search).

Google's own careers site (careers.google.com, served under
google.com/about/careers/applications/jobs/results) is a fully open,
unauthenticated, server-rendered HTML page — no third-party ATS, no
bot-blocking encountered. See CLAUDE.md's "Meta, Amazon, Google, Apple,
Microsoft, IBM, Canonical scraping approach" section (Google bullet) for how
this was found.

**Known limitation, not a bug**: Google exposes no true category/team facet.
The UI's "what do you want to do?" field just resolves to the same free-text
`q=` quoted-phrase search used here (`q="Software Engineer"`), so this is a
best-effort text-match filter, not an exact category filter like RBC's
`category=` or Workday's `jobFamilyGroup` facets elsewhere in this project.
`location=Canada` IS a real server-side facet (confirmed via the results
page's own location chip) and matches jobs by ANY of their listed locations
— a job's *displayed* primary location (the first one shown in the listing)
can therefore be a non-Canada city even though the job is legitimately
multi-location and includes Canada (confirmed directly on one such job
during investigation). This scraper takes the listing's displayed location
as-is rather than fetching every detail page to find the "real" one, since
the job itself is still a genuine match returned by Google's own filter.

HTML structure (found via live inspection — CLAUDE.md deliberately didn't
give an exact selector):
- Each result is `<li class="lLd3Je" ssk="17:<numeric id>">` inside
  `<ul class="spHGqe">`.
- Title: `h3.QJPWVe` text.
- Location: `span.r0wTof` text (only the first/primary one if multi-location).
- Detail link: the `<a href="jobs/results/<id>-<slug>?...">` inside the
  `<li>` — relative to the *directory* of this page's own URL
  (`.../applications/jobs/`), so the canonical absolute URL is built
  directly from the numeric ID + slug rather than via naive urljoin (which
  double-prefixes "jobs/" — confirmed live).
- No posted-date field exists anywhere on the listing or detail page —
  `posted_date` is left `None`; the UI's fallback to `first_seen_at` (see
  CLAUDE.md's "Posted date fallback") is the sanctioned behavior here, not a
  workaround.
- Pagination: `page=N`, 1-indexed, page size 20 — confirmed live (a 25-hit
  query returned 20 results on page=1, the remaining 5 on page=2, and 0 on
  page=3).
"""

import logging
import re

import httpx
from bs4 import BeautifulSoup

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://www.google.com/about/careers/applications"
RESULTS_URL = f"{BASE_URL}/jobs/results"
LOCATION = "Canada"
QUERY = '"Software Engineer"'
CATEGORY_LABEL = "Software Engineer (free-text search)"

PAGE_SIZE = 20
MAX_PAGES = 50  # safety cap; this query currently returns a handful of pages


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()

    with httpx.Client(timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as client:
        for page in range(1, MAX_PAGES + 1):
            response = client.get(RESULTS_URL, params={"location": LOCATION, "q": QUERY, "page": page})
            response.raise_for_status()

            items = _extract_items(response.text)
            if not items:
                break

            for raw in items:
                job_id = raw["id"]
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                jobs.append(_normalize(raw))
        else:
            logger.warning("Google scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Google: fetched %d jobs", len(jobs))
    return jobs


def _extract_items(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for li in soup.select("li.lLd3Je"):
        ssk = li.get("ssk", "")
        match = re.match(r"^\d+:(\d+)$", ssk)
        if not match:
            continue
        job_id = match.group(1)

        title_el = li.select_one("h3.QJPWVe")
        location_el = li.select_one("span.r0wTof")
        link_el = li.select_one("a[href]")
        if not title_el or not link_el:
            logger.warning("Google: skipping job id=%s — missing title/link, site structure may have changed", job_id)
            continue

        items.append(
            {
                "id": job_id,
                "title": title_el.get_text(strip=True),
                "location": location_el.get_text(strip=True) if location_el else "",
                "href": link_el["href"],
            }
        )
    return items


def _normalize(raw: dict) -> NormalizedJob:
    slug_match = re.search(r"jobs/results/\d+-([^?]+)", raw["href"])
    slug = slug_match.group(1) if slug_match else ""
    url = f"{RESULTS_URL}/{raw['id']}-{slug}" if slug else f"{RESULTS_URL}/{raw['id']}"

    return {
        "external_id": raw["id"],
        "title": raw["title"],
        "url": url,
        "location": raw["location"],
        "category": CATEGORY_LABEL,
        "posted_date": None,
        "platform": "Google Careers (custom, in-house)",
    }
