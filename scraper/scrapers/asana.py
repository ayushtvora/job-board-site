"""Asana careers scraper, scoped to Canada + Engineering / Data.

Greenhouse (board token `asana`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 98 jobs, 17 in Canada (all
Vancouver). "Engineering" covers product engineering, security, IT and data
engineering; "Data" (under Product) covers data analytics.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {"Engineering", "Data"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Asana", board_token="asana", departments=DEPARTMENTS)
