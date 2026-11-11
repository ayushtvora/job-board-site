"""Block (Square, Cash App) careers scraper, scoped to Canada + engineering/data teams.

Greenhouse, board token `block`, via scrapers/greenhouse.py. Investigated
2026-11-10: 196 postings, 13 in Canada (Toronto, mostly Square sales).

- Departments are numbered cost centres like "10414 Engineering - Fintech
  Platform" and "10109 Risk - Risk ML & DS", so scope is any department
  whose name mentions Engineering, Data, ML or Analytics, rather than an
  exact department list.
"""

import re

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

TECH_DEPARTMENT_PATTERN = re.compile(r"engineering|\bdata\b|\bML\b|\bDS\b|analytics|security", re.IGNORECASE)


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(
        name="Block",
        board_token="block",
        departments=None,
        job_filter=lambda raw: any(TECH_DEPARTMENT_PATTERN.search(d["name"]) for d in raw.get("departments") or []),
    )
