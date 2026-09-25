"""Neo Financial careers scraper, scoped to Canada + Engineering / Data Science.

Ashby public job-board API (org `neofinancial`; `neo` doesn't exist), via
the shared helper in scrapers/ashby.py. Investigated 2026-09-25: 79 jobs,
all in Canada (Calgary / Winnipeg), 70 of them sales.
"""

from .ashby import scrape_ashby
from .base import NormalizedJob

DEPARTMENTS = {"Engineering", "Data Science"}


def scrape() -> list[NormalizedJob]:
    return scrape_ashby(name="Neo Financial", org="neofinancial", departments=DEPARTMENTS)
