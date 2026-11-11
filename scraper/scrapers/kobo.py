"""Rakuten Kobo careers scraper (Canada, development job families).

Workday CXS API, Rakuten's tenant `rakuten.wd1.myworkdayjobs.com`, site
`Kobo`, via scrapers/workday_cxs.py (rakutenkobo.com timed out from here;
the site name was found by probing). Investigated 2026-11-10: 8 postings,
6 in Canada, all Toronto and all "Development Engineering - RF".

- `locationCountry` Canada = the shared `a30a87ed…` ID.
- `jobFamily`: "Development Engineering - RF" and "Internet/e-Commerce - RF".
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
JOB_FAMILIES = [
    "c37e417fc77e01c2614f27b127003100",  # Development Engineering - RF
    "9a9ef1b18cc4011105923add27004700",  # Internet/e-Commerce - RF
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Rakuten Kobo",
        base_url="https://rakuten.wd1.myworkdayjobs.com",
        tenant="rakuten",
        site="Kobo",
        applied_facets={"jobFamily": JOB_FAMILIES, "locationCountry": [CANADA_FACET_ID]},
        category_label="Development Engineering",
    )
