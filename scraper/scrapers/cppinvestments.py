"""CPP Investments careers scraper, scoped to Canada + Engineering / security.

Workday CXS API, tenant `cppib.wd10.myworkdayjobs.com/cppinvestments`, via
the shared helper in scrapers/workday_cxs.py.

- `locationCountry` Canada = the shared `a30a87ed…` ID (36 of 44 jobs,
  2026-09-25).
- No `jobFamilyGroup` facet; `jobFamily` "Engineering" (19 jobs), plus
  "Information Security" and "Systematic Investments and Investment
  Engineering".
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
JOB_FAMILY_IDS = [
    "b0ac3ae20ece1001b52eb540fcb80000",  # Engineering
    "7dce790885fe1001ec5d035436a20000",  # Information Security
    "b0ac3ae20ece1001b22a66211feb0000",  # Systematic Investments and Investment Engineering
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="CPP Investments",
        base_url="https://cppib.wd10.myworkdayjobs.com",
        tenant="cppib",
        site="cppinvestments",
        applied_facets={"jobFamily": JOB_FAMILY_IDS, "locationCountry": [CANADA_FACET_ID]},
        category_label="Engineering",
    )
