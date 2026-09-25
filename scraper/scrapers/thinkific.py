"""Thinkific careers scraper, scoped to Canada + Research and Development.

Ashby public job-board API (org `thinkific`), via the shared helper in
scrapers/ashby.py. Thinkific also has a Greenhouse board with the same
token, but it's empty (0 jobs, 2026-09-25); Ashby is the live one, with 1
Canadian R&D engineering posting at investigation time.
"""

from .ashby import scrape_ashby
from .base import NormalizedJob


def scrape() -> list[NormalizedJob]:
    return scrape_ashby(name="Thinkific", org="thinkific", departments={"Research and Development"})
