"""Air Canada careers scraper, scoped to Digital and Technology.

`careers.aircanada.com` is Phenom People, same `phApp.ddo` blob family as
RBC/BMO/Bell, via the shared helper in scrapers/phenom.py. The job pages
reference **Taleo** as the system of record, and the blob has no
`applyUrl` (`externalApply` is false), so the job URL comes from the
template and `platform` = "Taleo", following the record-the-real-backend
convention.

- `?category=Digital and Technology` filters server-side (10 of 71 jobs,
  2026-09-25). The site's `/ca/en/` section is Canada-only (`country` =
  "CANADA" on every job).
"""

from .base import NormalizedJob
from .phenom import scrape_phenom


def scrape() -> list[NormalizedJob]:
    return scrape_phenom(
        name="Air Canada",
        list_url="https://careers.aircanada.com/ca/en/search-results",
        job_url_template="https://careers.aircanada.com/ca/en/job/{job_id}",
        categories=["Digital and Technology"],
        platform="Taleo",
    )
