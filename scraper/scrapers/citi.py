"""Citi careers scraper (Canada, Technology and analytics job families).

Workday CXS API, tenant `citi.wd5.myworkdayjobs.com`, site `2` (yes, just
"2"; it's what jobs.citi.com, a Radancy TalentBrew front-end, links to),
via scrapers/workday_cxs.py. Investigated 2026-11-10.

- `Country_and_Jurisdiction` Canada = the shared `a30a87ed…` ID (198
  postings, almost all Mississauga, Citi's Canadian tech hub, plus
  Toronto).
- `jobFamilyGroup`: Technology, Decision Management (Citi's
  analytics/modelling family) and Data Governance.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
JOB_FAMILY_GROUPS = [
    "e32326e1708d01575bddff0c120102c1",  # Technology
    "e32326e1708d0106eb75f50c1201dac0",  # Decision Management
    "538c239234271000c428fd3827220000",  # Data Governance
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Citi",
        base_url="https://citi.wd5.myworkdayjobs.com",
        tenant="citi",
        site="2",
        applied_facets={"jobFamilyGroup": JOB_FAMILY_GROUPS, "Country_and_Jurisdiction": [CANADA_FACET_ID]},
        category_label="Technology",
    )
