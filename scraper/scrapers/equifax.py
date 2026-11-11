"""Equifax careers scraper (Canada, tech and data job families).

Workday CXS API, tenant `equifax.wd5.myworkdayjobs.com/External`, via
scrapers/workday_cxs.py. careers.equifax.com is Akamai-403'd to plain
HTTP, but the Workday API isn't. Investigated 2026-11-10: 166 postings
worldwide, 12 in Canada (Toronto, Montreal).

- `locationCountry` Canada = the shared `a30a87ed…` ID.
- `jobFamilyGroup`: "Tech Dev and Client Services", "Data and Analytics",
  "Tech Engineering and Services Ops".
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
JOB_FAMILY_GROUPS = [
    "c7903293292c107a0ba489af772447a7",  # Tech Dev and Client Services
    "c7903293292c107a0ba47d2594ac479b",  # Data and Analytics
    "c7903293292c107a0ba48bef0eb447a9",  # Tech Engineering and Services Ops
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Equifax",
        base_url="https://equifax.wd5.myworkdayjobs.com",
        tenant="equifax",
        site="External",
        applied_facets={"jobFamilyGroup": JOB_FAMILY_GROUPS, "locationCountry": [CANADA_FACET_ID]},
        category_label="Technology",
    )
