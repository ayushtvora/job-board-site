"""Tenstorrent careers scraper, scoped to Canada + AI software / hardware engineering.

Greenhouse (board token `tenstorrent`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 123 jobs, 45 with Toronto
among their locations. Many are posted to several cities at once
("Austin; Santa Clara; Toronto"), and those are kept.

Departments are top-level engineering orgs with sub-teams ("AI SW: Runtime",
"Systems Engineering: PCB/Power", ...), so the parents are listed and the
helper walks the tree. "Operations" and "Experience" are left out.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {"AI SW", "AI Hardware", "Systems Engineering", "SoC", "Infrastructure"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Tenstorrent", board_token="tenstorrent", departments=DEPARTMENTS)
