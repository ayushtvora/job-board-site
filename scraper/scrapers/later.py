"""Later careers scraper, scoped to Canada + Technology / Data.

Greenhouse, board token `later`, via scrapers/greenhouse.py (later.com
embeds the board). Investigated 2026-11-10: 30 postings, 19 in Canada,
almost all Vancouver. Departments: "Technology" (engineering, MLOps) and
"Data".
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Later", board_token="later", departments={"Technology", "Data"})
