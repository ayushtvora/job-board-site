"""BCAA careers scraper (Information Technology job category).

Workday CXS, tenant `bcaa.wd3.myworkdayjobs.com/bcaacareers` (linked from
bcaa.com/about-us/careers), via scrapers/workday_cxs.py.

- Every location is in BC, so no country facet is needed.
- Category facet `jobFamilyGroup`, "Information Technology" =
  `25ae589691dd01fe130456399749e007` (4 of 39 jobs on 2026-10-02, e.g.
  Guidewire developers at the Burnaby head office).
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

IT_CATEGORY_ID = "25ae589691dd01fe130456399749e007"


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="BCAA",
        base_url="https://bcaa.wd3.myworkdayjobs.com",
        tenant="bcaa",
        site="bcaacareers",
        applied_facets={"jobFamilyGroup": [IT_CATEGORY_ID]},
        category_label="Information Technology",
    )
