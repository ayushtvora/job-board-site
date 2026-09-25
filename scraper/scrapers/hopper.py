"""Hopper careers scraper, scoped to Canada + engineering / data teams.

Ashby public job-board API (org `hopper`), via the shared helper in
scrapers/ashby.py. Investigated 2026-09-25: 27 jobs, 8 in Canada
(Montréal / remote).

Hopper uses `department` for the product area ("Travel Tech", "CX",
"Service") and `team` for the discipline ("Engineering", "Product
Management"), so jobs are matched on `team` instead of department.
"""

import re

from .ashby import scrape_ashby
from .base import NormalizedJob

TEAM_PATTERN = re.compile(r"engineer|data|machine learning|security|infrastructure", re.IGNORECASE)


def scrape() -> list[NormalizedJob]:
    return scrape_ashby(
        name="Hopper",
        org="hopper",
        departments=None,
        job_filter=lambda raw: bool(TEAM_PATTERN.search(raw.get("team") or "")),
    )
