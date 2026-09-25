"""PayPal careers scraper, scoped to Canada + Technology.

Workday CXS API, tenant `paypal.wd1.myworkdayjobs.com/jobs`
(careers.pypl.com is 403'd to plain HTTP), via the shared helper in
scrapers/workday_cxs.py.

- Category facet `jobFamilyGroup`: "Technology Job Family Group" =
  `b00c2f6141401001c5f81018e4210000` (software, cybersecurity, data and ML
  engineering job families).
- No country facet; the only Canadian `locations` value is "Toronto,
  Ontario, Canada" (1 posting, non-tech, on 2026-09-25), so that ID is
  passed. A new Canadian city won't be picked up until it's added here.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

TECHNOLOGY_FACET_ID = "b00c2f6141401001c5f81018e4210000"
CANADA_LOCATION_IDS = ["bcdc9518960a019b87f6b4a92d249098"]  # Toronto, Ontario, Canada


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="PayPal",
        base_url="https://paypal.wd1.myworkdayjobs.com",
        tenant="paypal",
        site="jobs",
        applied_facets={"jobFamilyGroup": [TECHNOLOGY_FACET_ID], "locations": CANADA_LOCATION_IDS},
        category_label="Technology",
    )
