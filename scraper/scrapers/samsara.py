"""Samsara careers scraper, scoped to Canada + Engineering / Business Technology / Hardware.

Greenhouse (board token `samsara`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 247 jobs, 31 in Canada
(mostly "Remote - Canada"). Product Design sits under Engineering here and
is excluded.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {"Engineering", "Business Technology", "Hardware"}
EXCLUDE = {"Product Design"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Samsara", board_token="samsara", departments=DEPARTMENTS, exclude_departments=EXCLUDE)
