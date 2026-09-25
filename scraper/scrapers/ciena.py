"""Ciena careers scraper, scoped to Canada + Engineering / IT / Data / Intern.

Workday CXS API, tenant `ciena.wd5.myworkdayjobs.com/Careers` (Ottawa is
Ciena's largest R&D site), via the shared helper in scrapers/workday_cxs.py.
careers.ciena.com is 403'd to plain HTTP.

- `Location_Country` Canada = the shared `a30a87ed…` ID (75 of 147 jobs,
  2026-09-25).
- Category facet `jobFamilyGroup`: "Engineering (Group)", "IT (Group)",
  "Data Analytics (Group)", and "Intern (Group)" (Ottawa co-ops, mostly
  software).
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
CATEGORY_FACET_IDS = [
    "f08e25a5d78010903df730510aefa016",  # Engineering (Group)
    "f08e25a5d78010903df743451bd7a026",  # IT (Group)
    "a99b196937e201240bf49f6817016ee4",  # Data Analytics (Group)
    "f08e25a5d78010903df740ea6ac7a024",  # Intern (Group)
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Ciena",
        base_url="https://ciena.wd5.myworkdayjobs.com",
        tenant="ciena",
        site="Careers",
        applied_facets={"jobFamilyGroup": CATEGORY_FACET_IDS, "Location_Country": [CANADA_FACET_ID]},
        category_label="Engineering / IT",
    )
