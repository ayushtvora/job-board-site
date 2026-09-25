"""Wealthsimple careers scraper, scoped to Canada + Data & Engineering.

Ashby public job-board API (org `wealthsimple`), via the shared helper in
scrapers/ashby.py. Investigated 2026-09-25: all 43 jobs are Canadian
(mostly "Remote (Canada)"), so the Canada filter is effectively a no-op
here but kept for safety. Department "Data & Engineering" covers the
Engineering, Platform Engineering, Security, and data teams.
"""

from .ashby import scrape_ashby
from .base import NormalizedJob

DEPARTMENTS = {"Data & Engineering"}


def scrape() -> list[NormalizedJob]:
    return scrape_ashby(name="Wealthsimple", org="wealthsimple", departments=DEPARTMENTS)
