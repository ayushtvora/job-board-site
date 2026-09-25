"""Figma careers scraper, scoped to Canada + Engineering.

Greenhouse (board token `figma`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 163 jobs.

**Canada caveat**: no posting has a Canadian `location.name` (it's
"San Francisco, CA • New York, NY • United States"), but 53 postings list a
"Canada" office alongside "US". The helper's default check matches offices,
so those postings count as Canada here. That tagging is Figma's own, but
the posting text may still say US hubs only.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Figma", board_token="figma", departments={"Engineering"})
