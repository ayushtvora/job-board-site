"""Jobber careers scraper, scoped to Canada + Product Engineering.

Ashby public job-board API (org `jobber`), via the shared helper in
scrapers/ashby.py. Investigated 2026-09-25: 40 jobs, 39 in Canada
(Edmonton / Toronto / remote). Engineering is the "Product Engineering"
department; "Engineering" and "Data" are listed too in case Jobber
splits them out later.
"""

from .ashby import scrape_ashby
from .base import NormalizedJob

DEPARTMENTS = {"Product Engineering", "Engineering", "Data"}


def scrape() -> list[NormalizedJob]:
    return scrape_ashby(name="Jobber", org="jobber", departments=DEPARTMENTS)
