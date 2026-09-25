"""Fortinet careers scraper, scoped to Canada + software / hardware development.

Fortinet's careers site is **Oracle Recruiting Cloud**, pod
`edel.fa.us2.oraclecloud.com`, site `CX_1`, via the shared helper in
scrapers/oracle_recruiting.py. (`CX_2001` returns the same set; Fortinet
Federal is a separate pod.)

- `selectedLocationsFacet` Canada = `300000000361286` (132 of 935 jobs,
  2026-09-25; 93 in Burnaby, the rest Ottawa/Toronto/Montréal/Calgary).
- The categories facet only lists the top 10 values. These were read with
  the Canada filter applied: "Software Development", "Release QA",
  "Software-Dev QA", "Embedded SW/Firmware Engineering", "Web Development",
  "Hardware Development". "Systems Engineering" here means pre-sales SEs,
  so it's left out.
"""

from .base import NormalizedJob
from .oracle_recruiting import scrape_oracle_recruiting

CANADA_FACET_ID = "300000000361286"
CATEGORY_FACET_IDS = [
    "300000009998482",  # Software Development
    "300000009998518",  # Release QA
    "300000010292243",  # Software-Dev QA
    "300000010292412",  # Embedded SW/Firmware Engineering
    "300000010292298",  # Web Development
    "300000010292368",  # Hardware Development
]


def scrape() -> list[NormalizedJob]:
    return scrape_oracle_recruiting(
        name="Fortinet",
        host="edel.fa.us2.oraclecloud.com",
        finder_filters={
            "selectedLocationsFacet": CANADA_FACET_ID,
            "selectedCategoriesFacet": ";".join(CATEGORY_FACET_IDS),
        },
        category_label="Software Development",
    )
