"""Cadence Design Systems careers scraper, scoped to Canada.

Workday CXS API, tenant `cadence.wd1.myworkdayjobs.com/External_Careers`,
via the shared helper in scrapers/workday_cxs.py. (`Univ_Careers` is the
separate campus site.)

- `Location_Country` Canada = the shared `a30a87ed…` ID (16 of 615 jobs,
  2026-09-25: Montréal, Burnaby, Toronto, remote by province).
- This tenant exposes **no category facet**. Nearly all Canadian postings
  are design/verification/software engineering, so everything in Canada is
  kept; the title shows the rare non-engineering one.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Cadence",
        base_url="https://cadence.wd1.myworkdayjobs.com",
        tenant="cadence",
        site="External_Careers",
        applied_facets={"Location_Country": [CANADA_FACET_ID]},
        category_label="Engineering",
    )
