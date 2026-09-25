"""League careers scraper, scoped to Canada + engineering departments.

Greenhouse (board token `leagueinc`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 13 jobs, 10 in Canada
(Toronto). The only engineering department currently in the tree is
"Security Engineering"; "Engineering" and "Data" are listed too, so new
postings there are picked up when those departments come back.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {"Engineering", "Security Engineering", "Data"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="League", board_token="leagueinc", departments=DEPARTMENTS)
