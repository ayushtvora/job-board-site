"""Pinterest careers scraper, scoped to Canada + engineering departments.

Greenhouse (board token `pinterest`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 153 jobs total, 10 in
Toronto (`location.name` like "Toronto, ON, CA" — note the trailing "CA"
is Canada's country code here, while US jobs use "..., CA, US" for
California; the helper's pattern only matches whole-word province codes
and "Toronto", so neither form is mis-matched).

Departments: everything under the "Engineering, Product and Design (L2)"
parent, minus "Design" and "Core Product" (non-engineering sub-teams).
That keeps Core/Data/Oversight Engineering, EPD Ads, ATG, Infrastructure
and SRE, Security, and IT.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {"Engineering, Product and Design (L2)"}
EXCLUDE_DEPARTMENTS = {"Design", "Core Product"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(
        name="Pinterest",
        board_token="pinterest",
        departments=DEPARTMENTS,
        exclude_departments=EXCLUDE_DEPARTMENTS,
    )
