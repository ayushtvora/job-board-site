"""Loopio careers scraper, scoped to Canada + Product Engineering.

Ashby public job-board API (org `loopio`), via the shared helper in
scrapers/ashby.py. Investigated 2026-09-25: 13 jobs, all in Canada
(Toronto / remote). The "Product" department mixes product engineering,
product management and product marketing, so jobs are matched on `team`
("Product Engineering", or any other engineering/data team).
"""

import re

from .ashby import scrape_ashby
from .base import NormalizedJob

TEAM_PATTERN = re.compile(r"engineer|data|security", re.IGNORECASE)


def scrape() -> list[NormalizedJob]:
    return scrape_ashby(
        name="Loopio",
        org="loopio",
        departments=None,
        job_filter=lambda raw: bool(TEAM_PATTERN.search(raw.get("team") or "")),
    )
