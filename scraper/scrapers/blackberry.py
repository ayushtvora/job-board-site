"""BlackBerry careers scraper (BlackBerry + QNX), scoped to Canada + Product Development.

Workday CXS API, tenant `bb.wd3.myworkdayjobs.com` (linked from
blackberry.com/en/careers), via the shared helper in scrapers/workday_cxs.py.
The tenant has separate sites for `BlackBerry` and its `QNX` division
(plus a `Student` site), each scraped with the same facets and merged.

- `Country` Canada = the shared `a30a87ed…` ID (Ottawa, Waterloo).
- `Functional_Area` "Product Development" =
  `c756b1bbadec10e14dc41446721441c6` (15 postings on each site,
  2026-09-25). The two sites overlap, so results are de-duplicated on req ID.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
PRODUCT_DEVELOPMENT_FACET_ID = "c756b1bbadec10e14dc41446721441c6"
SITES = ["BlackBerry", "QNX"]


def scrape() -> list[NormalizedJob]:
    jobs: dict[str, NormalizedJob] = {}
    for site in SITES:
        for job in scrape_workday(
            name=f"BlackBerry ({site})",
            base_url="https://bb.wd3.myworkdayjobs.com",
            tenant="bb",
            site=site,
            applied_facets={"Functional_Area": [PRODUCT_DEVELOPMENT_FACET_ID], "Country": [CANADA_FACET_ID]},
            category_label="Product Development",
        ):
            jobs.setdefault(job["external_id"], job)
    return list(jobs.values())
