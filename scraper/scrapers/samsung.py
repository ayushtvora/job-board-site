"""Samsung careers scraper (Canada, R&D job families, plus Samsung Research's Toronto AI Center).

Two sources, merged:

- Samsung's global Workday tenant `sec.wd3.myworkdayjobs.com/Samsung_Careers`
  (linked from research.samsung.com/careers), via scrapers/workday_cxs.py.
  Investigated 2026-11-10: 644 postings, 13 in Canada (mostly Samsung
  Electronics Canada in Mississauga). `Location_Country` Canada = the
  shared `a30a87ed…` ID; `jobFamilyGroup` "R&D (JFG)" and "Software R&D (JFG)".
- Samsung Research America's Greenhouse board (`samsungresearchamerica`),
  which posts the Toronto AI Center's roles (1 on 2026-11-10, its head).
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
JOB_FAMILY_GROUPS = [
    "189767dd6c9201b4198fe1a6db2997c7",  # R&D (JFG)
    "189767dd6c9201e189e3eaa6db299dc7",  # Software R&D (JFG)
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Samsung",
        base_url="https://sec.wd3.myworkdayjobs.com",
        tenant="sec",
        site="Samsung_Careers",
        applied_facets={"jobFamilyGroup": JOB_FAMILY_GROUPS, "Location_Country": [CANADA_FACET_ID]},
        category_label="R&D",
    ) + scrape_greenhouse(name="Samsung Research America", board_token="samsungresearchamerica", departments=None)
