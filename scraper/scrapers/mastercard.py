"""Mastercard careers scraper, scoped to Canada + engineering / data / technology.

careers.mastercard.com is a Phenom front-end over Workday; the tenant is
`mastercard.wd1.myworkdayjobs.com/CorporateCareers` (linked from that
page), scraped directly via the shared helper in scrapers/workday_cxs.py.

- Category facet `jobFamilyGroup`: "Engineering", "AI & Data", "Technology
  Design and Development", "Technology Services", "Corporate Security".
- No country facet; the Canadian `locations` values are Toronto (incl. the
  Ethoca and University variants) and two separate "Vancouver, Canada"
  IDs, all passed (2026-09-25). A new Canadian city won't be picked up
  until it's added here.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CATEGORY_FACET_IDS = [
    "189119ebe266100103737c3d6a6e0000",  # Engineering
    "0ea6171d1dd81001035429e2c6b00000",  # AI & Data
    "866c0ed135ff106f00587685e7483440",  # Technology Design and Development
    "866c0ed135ff106f00a52e9d27783579",  # Technology Services
    "ef682c24739410700797d3388abcc077",  # Corporate Security
]
CANADA_LOCATION_IDS = [
    "abb6e89c39b847c49cb2958e421072b3",  # Toronto, Canada
    "bea842055ec0010f8fa2f063710e65dd",  # Toronto, Canada (Ethoca)
    "afef5ffa7f5c100100e055d60de90000",  # Toronto, Canada (University)
    "15854e620ab6014e5c345533ce3e0c5d",  # Vancouver, Canada
    "01e5081da6f8102e9926fe1ecf1d3147",  # Vancouver, Canada
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Mastercard",
        base_url="https://mastercard.wd1.myworkdayjobs.com",
        tenant="mastercard",
        site="CorporateCareers",
        applied_facets={"jobFamilyGroup": CATEGORY_FACET_IDS, "locations": CANADA_LOCATION_IDS},
        category_label="Engineering / Technology",
    )
