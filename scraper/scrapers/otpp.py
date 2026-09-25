"""Ontario Teachers' Pension Plan careers scraper, scoped to Toronto + Information Technology.

Workday CXS API, tenant `otppb.wd3.myworkdayjobs.com/OntarioTeachers_Careers`
(linked from otpp.com), via the shared helper in scrapers/workday_cxs.py.

- Category facet is `JobAreas` ("Functional Area"): "Information
  Technology" = `1d3992493f53018f7d0460bcd833528d` (6 of 37 jobs,
  2026-09-25).
- No country facet; the only Canadian `locations` value is "Toronto,
  Canada" (the others are London, Hong Kong, etc.).
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

IT_FACET_ID = "1d3992493f53018f7d0460bcd833528d"
TORONTO_LOCATION_ID = "b6f626b7ab7701a0ae5ecf057c39295f"


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Ontario Teachers'",
        base_url="https://otppb.wd3.myworkdayjobs.com",
        tenant="otppb",
        site="OntarioTeachers_Careers",
        applied_facets={"JobAreas": [IT_FACET_ID], "locations": [TORONTO_LOCATION_ID]},
        category_label="Information Technology",
    )
