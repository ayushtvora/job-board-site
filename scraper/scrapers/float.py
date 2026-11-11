"""Float careers scraper, scoped to Canada + Engineering.

Ashby, org `float` (floatfinancial.com/careers embeds `jobs.ashbyhq.com/Float`),
via scrapers/ashby.py. Investigated 2026-11-10: 16 postings, all Canadian
(Toronto, remote Canada). Engineering is the "Engineering" department.
"""

from .ashby import scrape_ashby
from .base import NormalizedJob


def scrape() -> list[NormalizedJob]:
    return scrape_ashby(name="Float", org="float", departments={"Engineering"})
