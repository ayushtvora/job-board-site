"""Brookfield careers scraper (Canada, technology job families).

Workday CXS API, tenant `brookfield.wd5.myworkdayjobs.com/Brookfield`
(Brookfield Asset Management and its operating companies), via
scrapers/workday_cxs.py. Investigated 2026-11-10: 143 postings, 61 in
Canada, nearly all Toronto.

- `locationCountry` Canada = the shared `a30a87ed…` ID.
- `jobFamily` (no `jobFamilyGroup` here): "Global BAM - Technology
  Services", "Real Estate OpCos - Technology", "BAM Op Co Technology
  Services".
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
JOB_FAMILIES = [
    "3653fa437add1001ec0b3c489a170000",  # Global BAM - Technology Services
    "753cc556f8381001ede8cbb75b980000",  # Real Estate OpCos - Technology
    "5805820d190b01d0adc7e20361010142",  # BAM Op Co Technology Services
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Brookfield",
        base_url="https://brookfield.wd5.myworkdayjobs.com",
        tenant="brookfield",
        site="Brookfield",
        applied_facets={"jobFamily": JOB_FAMILIES, "locationCountry": [CANADA_FACET_ID]},
        category_label="Technology",
    )
