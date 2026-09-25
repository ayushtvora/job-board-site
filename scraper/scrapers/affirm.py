"""Affirm careers scraper, scoped to Canada + Engineering / InfoSec & IT.

Greenhouse (board token `affirm`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 184 jobs, 93 in Canada
(almost all "Remote Canada"). "Engineering" covers Infrastructure Platform,
Checkout, Consumer and Financial Platforms engineering.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {"Engineering", "InfoSec & IT"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Affirm", board_token="affirm", departments=DEPARTMENTS)
