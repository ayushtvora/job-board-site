"""UBC careers scraper, scoped to M&P Information Systems & Tech staff jobs.

Same Workday CXS API approach as SOTI (scrapers/soti.py) — see that module's
docstring for how this pattern works in general. UBC-specific notes:

- UBC runs three separate Workday sites by employee type; staff jobs are the
  relevant one here. Tenant/site: `ubc.wd10.myworkdayjobs.com/ubcstaffjobs`.
- **No country filter is applied or needed** — every location facet value on
  this site is already a BC campus (Vancouver/Okanagan), so there's nothing
  to narrow to Canada.
- Category facet here is `jobFamily` (not `jobFamilyGroup` like the other
  Workday tenants in this project) — a finer-grained, union/role-based
  facet on this site. Closest Software-Engineering equivalent, confirmed
  against actual returned job titles ("Programmer Systems Analyst II",
  "Support Analyst I", "Network Analyst I, Wireless"):
  `"M&P Information Systems & Tech"` = `0f50d6e300ee011d7120b51e4001a9f9`.
- `bulletFields` is single-element here (`[reqId]`) — `category` is
  hardcoded to the filtered facet's label, same reasoning as SOTI.
- Posted date and canonical apply URL: same as SOTI, from each job's detail
  endpoint (`jobPostingInfo.startDate` / `.externalUrl`).
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

# Opaque Workday facet ID, not derivable from its label — confirmed against
# the site's own facet metadata (see module docstring).
CATEGORY_FACET_ID = "0f50d6e300ee011d7120b51e4001a9f9"  # M&P Information Systems & Tech


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="UBC",
        base_url="https://ubc.wd10.myworkdayjobs.com",
        tenant="ubc",
        site="ubcstaffjobs",
        applied_facets={"jobFamily": [CATEGORY_FACET_ID]},
        category_label="M&P Information Systems & Tech",
    )
