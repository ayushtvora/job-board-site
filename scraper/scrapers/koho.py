"""KOHO careers scraper, scoped to Canada + Technology / Data.

Ashby public job-board API (org `koho`), via the shared helper in
scrapers/ashby.py. Investigated 2026-09-25: 9 jobs, all in Canada;
"Technology" (e.g. its Security team) and "Data" (Analytics Engineering)
are the tech departments.
"""

from .ashby import scrape_ashby
from .base import NormalizedJob

DEPARTMENTS = {"Technology", "Data"}


def scrape() -> list[NormalizedJob]:
    return scrape_ashby(name="KOHO", org="koho", departments=DEPARTMENTS)
