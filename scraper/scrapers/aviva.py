"""Aviva Canada careers scraper (Canada, Technology / Data / Digital).

Workday CXS API, tenant `aviva.wd1.myworkdayjobs.com/External` (linked
from aviva.ca/en/careers with the Canada facet), via
scrapers/workday_cxs.py. Investigated 2026-11-10: 131 postings, 100 in
Canada (Markham, Toronto, Montreal, Oakville).

- `Location_Country` Canada = the shared `a30a87ed…` ID.
- `jobFamilyGroup`: Technology, Data and Digital.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
JOB_FAMILY_GROUPS = [
    "ebd5f88987d24fb19b1d3f866956b409",  # Technology
    "6dffc31246041001d041c14828210000",  # Data
    "17229517dd041001d045f3a34c4e0000",  # Digital
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Aviva",
        base_url="https://aviva.wd1.myworkdayjobs.com",
        tenant="aviva",
        site="External",
        applied_facets={"jobFamilyGroup": JOB_FAMILY_GROUPS, "Location_Country": [CANADA_FACET_ID]},
        category_label="Technology",
    )
