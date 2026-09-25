"""Twilio careers scraper, scoped to Canada + Engineering / IT.

Greenhouse (board token `twilio`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 136 jobs, 11 in Canada
("Remote - Canada", plus province-level ones like "Remote - Ontario, Canada
(DNU)", where "DNU" is Twilio's own label). "Engineering" sits under R&D
and "IT" under G&A.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {"Engineering", "IT"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Twilio", board_token="twilio", departments=DEPARTMENTS)
