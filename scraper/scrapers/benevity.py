"""Benevity careers scraper, scoped to Canada + Technology.

Ashby public job-board API (org `benevity`), via the shared helper in
scrapers/ashby.py. Investigated 2026-09-25: 21 jobs, all in Canada
(Calgary). "Technology" (Engineering team) and "Technology Operations" are
the tech departments.
"""

from .ashby import scrape_ashby
from .base import NormalizedJob

DEPARTMENTS = {"Technology", "Technology Operations"}


def scrape() -> list[NormalizedJob]:
    return scrape_ashby(name="Benevity", org="benevity", departments=DEPARTMENTS)
