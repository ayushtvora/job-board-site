"""Salesforce careers scraper, scoped to Canada + Software Engineering.

Workday CXS API, via the shared helper in scrapers/workday_cxs.py (see its
docstring, and SOTI's, for how this pattern works in general). Salesforce-specific notes:

- Tenant/site: `salesforce.wd12.myworkdayjobs.com/External_Career_Site`.
- Category facet `jobFamilyGroup`, value `14fa3452ec7c1011f90d0002a2100000`
  = "Software Engineering".
- Country is a custom-field facet with a long tenant-specific parameter
  name (`CF_-_REC_-_LRV_-_Job_Posting_Anchor_-_Country_from_Job_Posting_Location_Extended`),
  but its Canada value is the shared cross-tenant
  `a30a87ed25634629aa6c3958aa2b91ea`. Cross-checked 2026-09-25 against
  passing every "Canada - <city>" value of the `locations` facet instead —
  both give the same result (currently just 1 job; Salesforce's other ~46
  Canada postings are in non-engineering categories).
- `bulletFields` is single-element (`[reqId]`), so `category` is hardcoded.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

# Opaque Workday facet IDs, confirmed against the tenant's own facet metadata.
COUNTRY_FACET_PARAM = "CF_-_REC_-_LRV_-_Job_Posting_Anchor_-_Country_from_Job_Posting_Location_Extended"
CATEGORY_FACET_ID = "14fa3452ec7c1011f90d0002a2100000"  # Software Engineering
COUNTRY_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"  # Canada


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Salesforce",
        base_url="https://salesforce.wd12.myworkdayjobs.com",
        tenant="salesforce",
        site="External_Career_Site",
        applied_facets={
            "jobFamilyGroup": [CATEGORY_FACET_ID],
            COUNTRY_FACET_PARAM: [COUNTRY_FACET_ID],
        },
        category_label="Software Engineering",
    )
