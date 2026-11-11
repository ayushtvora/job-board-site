"""AbCellera careers scraper, scoped to Canada + IT / bioinformatics.

Greenhouse, board token `abcellera`, via scrapers/greenhouse.py
(abcellera.com/careers embeds it). Investigated 2026-11-10: 37 postings,
35 in Canada (Vancouver, Montreal), mostly regulatory and quality roles.
Department in scope: "Information Technology", plus data/software titles
anywhere (bioinformatics postings sit under scientific departments, mixed
with lab science roles).
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="AbCellera", board_token="abcellera", departments={"Information Technology"})
