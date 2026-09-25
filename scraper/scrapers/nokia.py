"""Nokia careers scraper, scoped to Canada + Applied R&D / Information Technology.

`jobs.nokia.com` is **Oracle Recruiting Cloud** (Nokia's own domain fronting
the Candidate Experience site `CX_1`), via the shared helper in
scrapers/oracle_recruiting.py. The REST API isn't served on jobs.nokia.com
itself (it 302s to an error page); the pod host
`fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com` is referenced from that
page's HTML and answers the API directly. Job links on the pod host work too.

- `selectedLocationsFacet` Canada = `300000000471544` (85 jobs, 2026-09-25,
  mostly Ottawa/Kanata; `PrimaryLocation` is just "Canada").
- `selectedCategoriesFacet`: "Applied R&D" = `300000009357764` (49 in
  Canada), "Information Technology" = `300000009357755`, semicolon-joined.
"""

from .base import NormalizedJob
from .oracle_recruiting import scrape_oracle_recruiting

CANADA_FACET_ID = "300000000471544"
CATEGORY_FACET_IDS = [
    "300000009357764",  # Applied R&D
    "300000009357755",  # Information Technology
]


def scrape() -> list[NormalizedJob]:
    return scrape_oracle_recruiting(
        name="Nokia",
        host="fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com",
        finder_filters={
            "selectedLocationsFacet": CANADA_FACET_ID,
            "selectedCategoriesFacet": ";".join(CATEGORY_FACET_IDS),
        },
        category_label="Applied R&D / IT",
    )
