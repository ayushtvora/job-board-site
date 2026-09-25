"""OMERS careers scraper, scoped to Canada + Information Technology / Analytics.

Workday CXS API, tenant `omers.wd3.myworkdayjobs.com/OMERS_External`, via
the shared helper in scrapers/workday_cxs.py.

- `locationCountry` Canada = the shared `a30a87ed…` ID (51 of 57 jobs,
  2026-09-25; the rest are New York / London investment roles).
- Category facet `jobFamilyGroup`: "Information Technology" and "Analytics
  and Reporting".
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
CATEGORY_FACET_IDS = [
    "6b4e4b163448010ad4fc4658f311e408",  # Information Technology
    "6b4e4b16344801944284951cf311d408",  # Analytics and Reporting
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="OMERS",
        base_url="https://omers.wd3.myworkdayjobs.com",
        tenant="omers",
        site="OMERS_External",
        applied_facets={"jobFamilyGroup": CATEGORY_FACET_IDS, "locationCountry": [CANADA_FACET_ID]},
        category_label="Information Technology",
    )
