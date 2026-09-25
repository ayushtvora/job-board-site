"""Dropbox careers scraper, scoped to Canada + EPD (Engineering, Product & Design).

Greenhouse (board token `dropbox`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 47 jobs total.

- Canada: Dropbox is remote-first ("Virtual First"); Canadian roles have
  `location.name` = "Remote - Canada: Select locations". Its `offices[]`
  are country buckets like "Canada; US" attached to *US* remote roles too,
  so this scraper checks `location.name` only — the helper's default
  (location + offices) would pull in US-remote jobs.
- Departments: Dropbox's tree is `<Sub Team> < <Team> < <Org>`; engineering
  lives under the top-level "EPD" org (e.g. "CTO-Data Science, AI Platform
  & Eng (Sub Team) < CTO Team < EPD"). Matching on the EPD ancestor also
  includes product-management sub-teams (e.g. "Prod - DocSend"), so
  "Product Team" is excluded; there's no finer engineering-only parent.
"""

from .base import NormalizedJob
from .greenhouse import location_name_is_canada, scrape_greenhouse

DEPARTMENTS = {"EPD"}
EXCLUDE_DEPARTMENTS = {"Product Team"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(
        name="Dropbox",
        board_token="dropbox",
        departments=DEPARTMENTS,
        exclude_departments=EXCLUDE_DEPARTMENTS,
        is_canada=location_name_is_canada,
    )
