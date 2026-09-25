"""CIBC careers scraper, scoped to Canada + Information Technology.

Same Workday CXS API approach as SOTI (scrapers/soti.py) — see that module's
docstring for how this pattern works in general. CIBC-specific notes:

- Tenant/site: `cibc.wd3.myworkdayjobs.com/search` (the "site" segment is
  `search`, not `Careers` as in SOTI's case — this varies per tenant and is
  just read off the site's own URL).
- Facet parameter names are `jobFamilyGroup` (Job Category) and `Country`,
  confirmed against the site's own facet metadata: `jobFamilyGroup`
  value `4bbe6c74e8a70126f29430a881012510` = "Information Technology",
  `Country` value `a30a87ed25634629aa6c3958aa2b91ea` = "Canada" — the same
  opaque Canada ID SOTI's job detail responses used, suggesting Workday
  reuses common reference IDs (like countries) across tenants.
- Unlike SOTI, `bulletFields` here is just `[reqId]` — no second field with
  a more specific category — so `category` is hardcoded to the filtered
  facet's label, same reasoning as SOTI's category.
- Posted date and canonical apply URL: same as SOTI, from each job's detail
  endpoint (`jobPostingInfo.startDate` / `.externalUrl`).
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

# Opaque Workday facet IDs, not derivable from their labels — confirmed
# against the site's own facet metadata (see module docstring).
CATEGORY_FACET_ID = "4bbe6c74e8a70126f29430a881012510"  # Information Technology
COUNTRY_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"  # Canada


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="CIBC",
        base_url="https://cibc.wd3.myworkdayjobs.com",
        tenant="cibc",
        site="search",
        applied_facets={"jobFamilyGroup": [CATEGORY_FACET_ID], "Country": [COUNTRY_FACET_ID]},
        category_label="Information Technology",
    )
