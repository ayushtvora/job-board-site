"""Hootsuite careers scraper, scoped to Canada + Development.

Greenhouse, board token `hootsuite`, via scrapers/greenhouse.py.
Investigated 2026-11-10: 11 postings, 6 in Canada. A SmartRecruiters
company `hootsuite` also exists (8 postings) but the Greenhouse board is
the one with current engineering postings. Engineering is the
"Development" department; its co-ops are under "Students" and get picked
up by title.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Hootsuite", board_token="hootsuite", departments={"Development"})
