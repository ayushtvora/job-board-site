"""American Express careers scraper (Canada / Technology and data categories).

careers.americanexpress.com is Oracle Recruiting Cloud (it redirects to
`/en/sites/CX_1`), backed by the pod host `egug.fa.us2.oraclecloud.com`,
via scrapers/oracle_recruiting.py.

- `selectedLocationsFacet` Canada = `300000000228588` (8 jobs on
  2026-10-02, all Toronto).
- `selectedCategoriesFacet`: Technology = `300000081299474`, Data Mgmt and
  Analytics = `300000573321731`, semicolon-joined. None of the 8 Canadian
  jobs were in these on 2026-10-02 (they were risk, compliance, sales and
  product roles), so an empty result is expected for now.
"""

from .base import NormalizedJob
from .oracle_recruiting import scrape_oracle_recruiting

CANADA_FACET_ID = "300000000228588"
CATEGORY_FACET_IDS = [
    "300000081299474",  # Technology
    "300000573321731",  # Data Mgmt and Analytics
]


def scrape() -> list[NormalizedJob]:
    return scrape_oracle_recruiting(
        name="American Express",
        host="egug.fa.us2.oraclecloud.com",
        finder_filters={
            "selectedLocationsFacet": CANADA_FACET_ID,
            "selectedCategoriesFacet": ";".join(CATEGORY_FACET_IDS),
        },
        category_label="Technology / Data",
    )
