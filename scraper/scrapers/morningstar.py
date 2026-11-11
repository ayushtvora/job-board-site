"""Morningstar careers scraper (Canada, Product Development / IT / Data Management).

Workday CXS API, tenant `morningstar.wd5.myworkdayjobs.com`, site
`Morningstar`, via scrapers/workday_cxs.py (careers.morningstar.com
redirects to a marketing page). Investigated 2026-11-10: 184 postings
worldwide, 16 in Canada, all Toronto. A smaller `Americas` site (10
postings) had none in Canada.

- `locationCountry` Canada = the shared `a30a87ed…` ID.
- `jobFamilyGroup`: Product Development (Morningstar's software
  engineers), IT and Data Management.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
JOB_FAMILY_GROUPS = [
    "de8ee3e7d69e1000cc24d352274c0000",  # Product Development
    "d77d9436ee661000cc27475616dc0000",  # IT
    "d77d9436ee661000cc272c48a8930000",  # Data Management
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Morningstar",
        base_url="https://morningstar.wd5.myworkdayjobs.com",
        tenant="morningstar",
        site="Morningstar",
        applied_facets={"jobFamilyGroup": JOB_FAMILY_GROUPS, "locationCountry": [CANADA_FACET_ID]},
        category_label="Product Development",
    )
