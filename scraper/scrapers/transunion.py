"""TransUnion careers scraper (Canada, tech and analytics job families).

Workday CXS API, tenant `transunion.wd5.myworkdayjobs.com/TransUnion`, via
scrapers/workday_cxs.py (transunion.com/careers is 403'd). Investigated
2026-11-10: 208 postings worldwide, 15 in Canada (Burlington, Toronto).

- `locationCountry` Canada = the shared `a30a87ed…` ID.
- `jobFamilyGroup`: Information Technology, Analytics, Data Management and
  Information Security family groups.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
JOB_FAMILY_GROUPS = [
    "d5a7b169652e015f9c4fb0be2b4bc1b7",  # Information Technology Family Group
    "d5a7b169652e01849a1a85be2b4bb7b7",  # Analytics Family Group
    "8ea54f386b200139dee11483ea014d11",  # Data Management Family Group
    "d5a7b169652e015c49161dbf2b4bdbb7",  # Information Security Family Group
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="TransUnion",
        base_url="https://transunion.wd5.myworkdayjobs.com",
        tenant="transunion",
        site="TransUnion",
        applied_facets={"jobFamilyGroup": JOB_FAMILY_GROUPS, "locationCountry": [CANADA_FACET_ID]},
        category_label="Technology",
    )
