"""Geotab careers scraper, scoped to Canada + Technology Development.

Greenhouse (board token `geotab`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 91 jobs total, 44
Canadian (Oakville HQ, Toronto, Waterloo, Burnaby).

- Departments: everything under the "Technology Development" parent
  (Geotab's engineering org — e.g. "Video", "OEM < Platform", "Altitude <
  Segment", product management), plus "IT" and "Security" (both under
  "Technical Services < Technical Operations").
- Canada is matched on `location.name` only: Geotab often posts the same
  role twice — once per country — and the US copy (e.g. "Atlanta, Georgia
  - USA") still lists Oakville among its `offices`, which the helper's
  default location+offices check would count as Canadian.
- A few real postings have the literal location name "z. Canada Job Post
  Template" (a Greenhouse location-template artifact on Geotab's side, not
  a test posting) — they still match as Canada and are kept as-is.
"""

from .base import CANADA_PATTERN, NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {"Technology Development", "IT", "Security"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Geotab", board_token="geotab", departments=DEPARTMENTS, is_canada=_is_canada)


def _is_canada(raw: dict) -> bool:
    return bool(CANADA_PATTERN.search((raw.get("location") or {}).get("name") or ""))
