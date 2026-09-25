"""Canadian Tire Corporation careers scraper, scoped to IT / Data / Digital.

Workday CXS API, tenant
`canadiantirecorporation.wd3.myworkdayjobs.com/Enterprise_External_Careers_Site`
(corp.canadiantire.ca is Akamai-403'd), via the shared helper in
scrapers/workday_cxs.py.

- Category facet `jobFamilyGroup` ("Specialty"): "Information Technology",
  "Data Analytics/Data Science", "eCommerce/Digital" (28 of 153 jobs,
  2026-09-25). The site spans all banners (Sport Chek, Mark's, CT Bank, ...)
  and is Canada-only, but `locationCountry` Canada is passed anyway.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
CATEGORY_FACET_IDS = [
    "a4710df742e51025f2508f0b0b410000",  # Information Technology
    "a4710df742e51025f2508a3c64f10000",  # Data Analytics/Data Science
    "a4710df742e51025f2508c0984b30002",  # eCommerce/Digital
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Canadian Tire",
        base_url="https://canadiantirecorporation.wd3.myworkdayjobs.com",
        tenant="canadiantirecorporation",
        site="Enterprise_External_Careers_Site",
        applied_facets={"jobFamilyGroup": CATEGORY_FACET_IDS, "locationCountry": [CANADA_FACET_ID]},
        category_label="Information Technology",
    )
