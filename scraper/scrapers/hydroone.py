"""Hydro One careers scraper, scoped to IT roles (by title).

`jobs.hydroone.com` is SAP SuccessFactors Jobs2Web, via the shared helper
in scrapers/jobs2web.py. (Not to be confused with jobs.hydro.com, which is
Norsk Hydro.)

- The only category landing pages are Corporate / Technical (trades) /
  Student, with no IT category and no Department column, so every job is
  fetched from `/search/` (42 on 2026-09-25, all Ontario) and IT roles are
  picked by title keyword.
"""

import re

from .base import NormalizedJob
from .jobs2web import scrape_jobs2web

TECH_TITLE_PATTERN = re.compile(
    r"software|developer|\bIT\b|information technology|data|cyber|security|cloud|architect|devops|digital|systems? analyst",
    re.IGNORECASE,
)


def scrape() -> list[NormalizedJob]:
    return scrape_jobs2web(
        name="Hydro One",
        base_url="https://jobs.hydroone.com",
        category_path=None,
        category_label="Information Technology",
        job_filter=lambda job: bool(TECH_TITLE_PATTERN.search(job["title"])),
    )
