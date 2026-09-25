"""Cisco careers scraper, scoped to Canada + Engineering / Information Technology.

Workday CXS API, tenant `cisco.wd5.myworkdayjobs.com/Cisco_Careers`
(cisco.com's careers page is Akamai-403'd; the tenant comes from public job
links), via the shared helper in scrapers/workday_cxs.py.

- Category facet `jobFamilyGroup`: "Engineering" =
  `2101eee3ea96016aef42a674fc016429` (655 jobs worldwide), "Information
  Technology" = `2101eee3ea96017b1ceba674fc016829`.
- **No country facet** on this tenant, only city-level `locations`. With
  ~670 matching jobs worldwide, filtering on the detail endpoint's country
  would cost ~670 requests a day, so every Canadian `locations` value
  (14 cities, 2026-09-25) is passed instead. A posting in a Canadian city
  added later won't be picked up until its ID is added here.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CATEGORY_FACET_IDS = [
    "2101eee3ea96016aef42a674fc016429",  # Engineering
    "2101eee3ea96017b1ceba674fc016829",  # Information Technology
]
CANADA_LOCATION_IDS = [
    "711bab74a75d1001f500b3d7e5700000",  # Calgary, Alberta
    "3dbd26f9e73e1001f4e292b3b8c30000",  # Fredericton, New Brunswick
    "026fa05becb01001f514203670d80000",  # Halifax, Nova Scotia
    "202bf7dfec311001f4d36aafe7890000",  # Kanata, Ontario
    "0696c83bbe641001f4fba75c72880000",  # Mississauga, Ontario
    "0696c83bbe641001f4fb1c843fe40000",  # Montreal, Quebec
    "ef8a5a22403d1001f505750d76990000",  # Ottawa, Ontario
    "6bed8334bf4b1001f4fd53276adb0000",  # Regina, Saskatchewan
    "8676de3331b41001f4f2e19952910000",  # Saint-Laurent, Quebec
    "ef8a5a22403d1001f507f5d83d750000",  # St. John's
    "026fa05becb01001f511983d851b0000",  # Toronto, Ontario
    "202bf7dfec311001f4d41cafa93e0000",  # Vancouver, British Columbia
    "0696c83bbe641001f4f950785ce30000",  # Winnipeg, Manitoba
    "3e81422748f91001f50476d015500000",  # Yellowknife, Northwest Territories
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Cisco",
        base_url="https://cisco.wd5.myworkdayjobs.com",
        tenant="cisco",
        site="Cisco_Careers",
        applied_facets={"jobFamilyGroup": CATEGORY_FACET_IDS, "locations": CANADA_LOCATION_IDS},
        category_label="Engineering / Information Technology",
    )
