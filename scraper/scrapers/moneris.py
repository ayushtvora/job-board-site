"""Moneris careers scraper (technology and data job families).

Workday CXS API, tenant `moneris.wd3.myworkdayjobs.com/Moneris`, via
scrapers/workday_cxs.py (moneris.com's careers page 404s; the site name
was found by probing). Investigated 2026-11-10: 32 postings, all in
Toronto, Montreal and Quebec City, so no country facet is needed (the
tenant has none).

- `jobFamilyGroup`: Technology Development & Platform Management,
  Technology Services Infrastructure and Ops, Data Science and Management,
  Technology, Information Security.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

JOB_FAMILY_GROUPS = [
    "907e24c89c030118c8aa691104cf0000",  # Technology Development & Platform Management
    "907e24c89c030118c8aa6addf3300000",  # Technology Services, Infrastructure and Ops
    "907e24c89c030118c8aa6b782a8b0000",  # Data Science and Management
    "907e24c89c030118c8aa6d45e43b0000",  # Technology
    "907e24c89c030118c8aa69aac2970000",  # Information Security
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Moneris",
        base_url="https://moneris.wd3.myworkdayjobs.com",
        tenant="moneris",
        site="Moneris",
        applied_facets={"jobFamilyGroup": JOB_FAMILY_GROUPS},
        category_label="Technology",
    )
