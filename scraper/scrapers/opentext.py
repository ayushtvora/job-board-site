"""OpenText careers scraper, scoped to Canada + Development / IT & Cloud Operations.

`careers.opentext.com` is Phenom People, via the shared helper in
scrapers/phenom.py. Like Bell, the blob has no `applyUrl`; OpenText's job
pages reference SuccessFactors as the backend, so `platform` =
"SuccessFactors".

- `?category=` filters server-side: "Development" = 46, "IT & Cloud
  Operations" = 56 (2026-09-25, all countries).
- **No working country param** (`country=Canada` is silently ignored — same
  as Adobe/Snowflake); each job's `country` is an ISO-3 code ("CAN" — 120
  of 367 jobs are Canadian, mostly Waterloo/Richmond Hill/Ottawa), filtered
  client-side.
- Job pages: `/us/en/job/<jobId>`.
"""

from .base import NormalizedJob
from .phenom import scrape_phenom


def scrape() -> list[NormalizedJob]:
    return scrape_phenom(
        name="OpenText",
        list_url="https://careers.opentext.com/us/en/search-results",
        job_url_template="https://careers.opentext.com/us/en/job/{job_id}",
        categories=["Development", "IT & Cloud Operations"],
        platform="SuccessFactors",
        job_filter=lambda raw: raw.get("country") in ("CAN", "Canada"),
    )
