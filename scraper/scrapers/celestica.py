"""Celestica careers scraper, scoped to Canada + Engineering.

`careers.celestica.com` is SAP SuccessFactors Jobs2Web (same layer as
Scotiabank/Rogers), via the shared helper in scrapers/jobs2web.py.

- Category landing page `/go/Engineering-Jobs/1280201/` (the other is
  Operations). It's worldwide, so Canada is filtered client-side on the
  row's location, which always ends in an ISO country code ("Toronto, ON,
  CA"). Only that suffix is checked: "Remote Employee Canada, NH, US" is a
  US posting despite the name. 1158 jobs site-wide on 2026-09-25, mostly
  manufacturing.
"""

from .base import NormalizedJob
from .jobs2web import scrape_jobs2web


def scrape() -> list[NormalizedJob]:
    return scrape_jobs2web(
        name="Celestica",
        base_url="https://careers.celestica.com",
        category_path="/go/Engineering-Jobs/1280201",
        category_label="Engineering",
        job_filter=lambda job: job["location"].endswith(", CA"),
    )
