"""Bell careers scraper, scoped to Technology + Operations & IT Infrastructure.

`jobs.bell.ca` is Phenom People, same `phApp.ddo` blob family as RBC/BMO,
via the shared helper in scrapers/phenom.py — plain HTTP GET, no browser.
Behind it, the system of record is SAP SuccessFactors (the job pages
reference SuccessFactors throughout, and the blob has no `applyUrl` —
`externalApply` is false), so `platform` = "SuccessFactors", following the
record-the-real-backend convention (RBC/BMO/Manulife).

- `?category=<label>` filters server-side (confirmed against the blob's own
  totalHits): "Technology" = 16, "Operations & IT Infrastructure" = 20
  (2026-09-25).
- The whole site is Canada-only (`country` facet = 100% Canada).
- Fields: `jobId` (stable numeric, external_id), `title`, `postedDate`,
  `category`/`subCategory` (e.g. "Software Development"), `location`,
  `multi_location`. Job pages are `/ca/en/job/<jobId>`.
"""

from .base import NormalizedJob
from .phenom import scrape_phenom


def scrape() -> list[NormalizedJob]:
    return scrape_phenom(
        name="Bell",
        list_url="https://jobs.bell.ca/ca/en/search-results",
        job_url_template="https://jobs.bell.ca/ca/en/job/{job_id}",
        categories=["Technology", "Operations & IT Infrastructure"],
        platform="SuccessFactors",
    )
