"""Capital One careers scraper (Toronto, tech and data job families).

Workday CXS API, tenant `capitalone.wd12.myworkdayjobs.com/Capital_One`,
via scrapers/workday_cxs.py. capitalonecareers.com is a Radancy TalentBrew
front-end over this tenant. Investigated 2026-11-10: 2,069 postings
worldwide.

- No country facet; the only Canadian `locations` value is
  "Toronto, ON" = `5303cb0ddb47102d5fab484784240953` (55 postings).
- `jobFamilyGroup`: Software-Engineering, AI & ML Engineering and
  Sciences, Data-Engineering, Analysis (Capital One's data analysts),
  Infrastructure Engineering, Cyber, Technology, Tech Delivery and Tech
  Operations. Anything else with a data/software title comes from the
  helper's keyword searches.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

TORONTO_LOCATION_ID = "5303cb0ddb47102d5fab484784240953"
JOB_FAMILY_GROUPS = [
    "23c40d87cd84100035bd7d9296540000",  # Software-Engineering
    "797094e02d441000c3f4fece96e10000",  # AI & ML Engineering and Sciences
    "23c40d87cd84100035bd9201b2bf0000",  # Data-Engineering
    "a12c70bf789e105802e9caf800542991",  # Analysis
    "c456977f3e611000c3e1be4b227f0000",  # Infrastructure Engineering
    "a3ffb53edaa61000c3f5dc76643a0000",  # Cyber
    "a12c70bf789e105802e9e79458dc29ab",  # Technology
    "797094e02d441000c3f51c4997090000",  # Tech Delivery
    "eaacc21c45691000c3e9ee9790cc0000",  # Tech Operations
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Capital One",
        base_url="https://capitalone.wd12.myworkdayjobs.com",
        tenant="capitalone",
        site="Capital_One",
        applied_facets={"jobFamilyGroup": JOB_FAMILY_GROUPS, "locations": [TORONTO_LOCATION_ID]},
        category_label="Technology",
    )
