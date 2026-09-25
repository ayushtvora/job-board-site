"""Definity Financial careers scraper, scoped to Technology / Data.

careers.definityfinancial.com links to **Oracle Recruiting Cloud**, pod
`hdks.fa.ca2.oraclecloud.com`, site `Careers-Definity`, via the shared
helper in scrapers/oracle_recruiting.py.

- All 85 jobs are in Canada (2026-09-25; Waterloo, Toronto, Calgary, ...),
  so no location filter is needed.
- `selectedCategoriesFacet`: "Technology and Systems" = `300002624297694`,
  "Data, Analytics and Business Intelligence" = `300002624297718`.
"""

from .base import NormalizedJob
from .oracle_recruiting import scrape_oracle_recruiting

CATEGORY_FACET_IDS = [
    "300002624297694",  # Technology and Systems
    "300002624297718",  # Data, Analytics and Business Intelligence
]


def scrape() -> list[NormalizedJob]:
    return scrape_oracle_recruiting(
        name="Definity",
        host="hdks.fa.ca2.oraclecloud.com",
        site_number="Careers-Definity",
        finder_filters={"selectedCategoriesFacet": ";".join(CATEGORY_FACET_IDS)},
        category_label="Technology and Systems",
    )
