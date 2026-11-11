"""Allstate Canada careers scraper (Canada, Technology and Data & Analytics).

Workday CXS API, tenant `allstate.wd5.myworkdayjobs.com/allstate_careers`
(allstate.ca/careers links to it with the Canada facet), via
scrapers/workday_cxs.py. Investigated 2026-11-10: 411 postings, 101 in
Canada (mostly agency sales in Markham, Toronto, Montreal).

- `Country` Canada = the shared `a30a87ed…` ID.
- `jobFamilyGroup`: Technology Group and Data & Analytics Group.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
JOB_FAMILY_GROUPS = [
    "bf1cc5a85e0b1002ffcbc04a1f4d0002",  # Technology Group
    "bf1cc5a85e0b1002ffcbc217c2580002",  # Data & Analytics Group
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Allstate",
        base_url="https://allstate.wd5.myworkdayjobs.com",
        tenant="allstate",
        site="allstate_careers",
        applied_facets={"jobFamilyGroup": JOB_FAMILY_GROUPS, "Country": [CANADA_FACET_ID]},
        category_label="Technology",
    )
