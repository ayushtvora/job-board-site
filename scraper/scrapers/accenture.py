"""Accenture careers scraper (Canada / technology "Area of Work" groups).

Workday CXS, tenant `accenture.wd103.myworkdayjobs.com/AccentureCareers`
(accenture.com's job search links to it), via scrapers/workday_cxs.py.

- Country facet `locationCountry`, Canada = the shared
  `a30a87ed25634629aa6c3958aa2b91ea` (146 jobs on 2026-10-02).
- Category facet `jobFamilyGroup` ("Area of Work"): Software Engineering,
  AI & Data, Technology & Information Architectures, Engineering &
  Networks, Information Technology Operations. That was 38 Canadian jobs.
  "Business & Technology Integration" is left out; it's mostly
  functional SAP/ServiceNow consulting.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
AREA_OF_WORK_IDS = [
    "bb69a804fb120130e52200ed1301d275",  # Software Engineering
    "99f04fef1b5710010b161504c3910000",  # AI & Data
    "bb69a804fb1201f7535003ed1301d875",  # Technology & Information Architectures
    "bb69a804fb120147d2f209ed1301e275",  # Engineering & Networks
    "bb69a804fb1201712ed6f3ec1301bc75",  # Information Technology Operations
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Accenture",
        base_url="https://accenture.wd103.myworkdayjobs.com",
        tenant="accenture",
        site="AccentureCareers",
        applied_facets={"locationCountry": [CANADA_FACET_ID], "jobFamilyGroup": AREA_OF_WORK_IDS},
        category_label="Technology",
    )
