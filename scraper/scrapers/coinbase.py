"""Coinbase careers scraper, scoped to Canada + Engineering.

Greenhouse (board token `coinbase`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 208 jobs total, ~9
Canadian (Coinbase is remote-first; Canadian roles are "Remote - Canada"
or office "Canada - Alberta").

Departments: the "Engineering" parent (Backend, Frontend, Infrastructure,
Data, Security, Managers sub-departments), plus the separate top-level
"Data Engineering" and "Security & Privacy" departments.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {"Engineering", "Data Engineering", "Security & Privacy"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Coinbase", board_token="coinbase", departments=DEPARTMENTS)
