"""Faire careers scraper, scoped to Canada + Engineering / Algorithms & Data.

Greenhouse (board token `faire`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 77 jobs total.

- Canada: Faire has Kitchener-Waterloo and Toronto offices. Several postings
  have a US-only `location.name` ("New York City, NY; San Francisco, CA")
  but list Toronto among their `offices` — the helper checks both, which
  is why ~30 jobs match rather than the ~19 a location-name-only check finds.
- Departments: "Engineering", "Algorithms & Data" (ML/data science), and
  "Security" (a child of "Information Technology").
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {"Engineering", "Algorithms & Data", "Security"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Faire", board_token="faire", departments=DEPARTMENTS)
