"""Cloudflare careers scraper, scoped to Canada + engineering departments.

Greenhouse (board token `cloudflare`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 393 jobs total.

- Canada: Cloudflare's `location.name` is just a work-style label
  ("Hybrid", "Distributed", "In-Office") — the actual city is only in
  `offices[]` (e.g. "Toronto, ON", "Canada", "Calgary, AB"), which the
  helper checks too.
- Departments: "Engineering", "Infrastructure", "Security", and "Emerging
  Technology and Incubation". Excluded: "Solution Engineering" (a pre-sales
  team under "Sales", despite the name) and "Customer Success Engineering".
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {"Engineering", "Infrastructure", "Security", "Emerging Technology and Incubation"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Cloudflare", board_token="cloudflare", departments=DEPARTMENTS)
