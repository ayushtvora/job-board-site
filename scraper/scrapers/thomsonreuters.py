"""Thomson Reuters careers scraper, scoped to Canada + Technology Careers.

Workday CXS API, via the shared helper in scrapers/workday_cxs.py (see its
docstring, and SOTI's, for how this pattern works in general). Thomson Reuters-specific
notes:

- Tenant/site: `thomsonreuters.wd5.myworkdayjobs.com/External_Career_Site`.
- Category facet is a custom field,
  `CF_Job_Posting_Anchor_Job_Category_EEB_Extended`, value
  `9276a62d4e68100204e60c54e1cc0001` = "Technology Careers" (the broad tech
  bucket; the finer `jobFamily` facet splits it into dozens of functions).
- Country facet is `Location_Country`, Canada = the shared cross-tenant
  `a30a87ed25634629aa6c3958aa2b91ea` (same as SOTI/CIBC/TD/Manulife/Sony).
  Combined filter confirmed 2026-09-25: 53 jobs.
- `bulletFields` is `[cities, provinces, reqId]` here — the req ID is the
  **last** element, not the first like every other Workday tenant so far —
  and `locationsText` is null on the list response, so location comes from
  the detail endpoint instead.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

# Opaque Workday facet IDs, confirmed against the tenant's own facet metadata.
CATEGORY_FACET_ID = "9276a62d4e68100204e60c54e1cc0001"  # Technology Careers
COUNTRY_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"  # Canada


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Thomson Reuters",
        base_url="https://thomsonreuters.wd5.myworkdayjobs.com",
        tenant="thomsonreuters",
        site="External_Career_Site",
        applied_facets={
            "CF_Job_Posting_Anchor_Job_Category_EEB_Extended": [CATEGORY_FACET_ID],
            "Location_Country": [COUNTRY_FACET_ID],
        },
        category_label="Technology Careers",
    )
