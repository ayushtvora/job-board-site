"""Workday (the company) careers scraper, scoped to Canada + engineering categories.

Workday hires through its own product — tenant
`workday.wd5.myworkdayjobs.com/Workday` — via the shared helper in
scrapers/workday_cxs.py. (Module is `workdayinc.py` to avoid confusion with
that helper; the company slug is "workday".)

- Category facet `jobFamilyGroup`: "Product Development and Engineering" =
  `8c5ce7a1cffb43e0a819c249a49fcb00`, "Engineering Operations and Services" =
  `a88cba90a00841e0b750341c541b9d56`, "Data Science, Business Intelligence
  and Analytics" = `4b2f970c50930155b9985193020a0c72`.
- Country facet `Location_Country`, Canada = the shared cross-tenant
  `a30a87ed25634629aa6c3958aa2b91ea`. Combined: 25 jobs (2026-09-25),
  mostly Vancouver (incl. the acquired Evisort AI team) and Toronto.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CATEGORY_FACET_IDS = [
    "8c5ce7a1cffb43e0a819c249a49fcb00",  # Product Development and Engineering
    "a88cba90a00841e0b750341c541b9d56",  # Engineering Operations and Services
    "4b2f970c50930155b9985193020a0c72",  # Data Science, Business Intelligence and Analytics
]
COUNTRY_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"  # Canada


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Workday",
        base_url="https://workday.wd5.myworkdayjobs.com",
        tenant="workday",
        site="Workday",
        applied_facets={"jobFamilyGroup": CATEGORY_FACET_IDS, "Location_Country": [COUNTRY_FACET_ID]},
        category_label="Engineering / Data Science",
    )
