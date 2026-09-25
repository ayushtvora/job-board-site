"""Sun Life careers scraper, scoped to Canada + IT job categories.

Workday CXS API, via the shared helper in scrapers/workday_cxs.py (see its
docstring, and SOTI's, for how this pattern works in general). Sun Life-specific notes:

- Tenant/site: `sunlife.wd3.myworkdayjobs.com/Experienced-Jobs` (the
  experienced-hire site; other plausible site names like `Careers` 404).
- Category facet is `jobFamily` (Sun Life has no broader `jobFamilyGroup`);
  three IT families together are the tech scope here:
  `b18e449d87914e8db756066e35d5f247` = "IT - Application Development",
  `fc46f3fb6ab24457be62e0b15c2c0101` = "IT - Technology Services",
  `9d42de6b15aa0173c155daaa6201da7f` = "IT - Digital Development".
- Country facet `Location_Country`, Canada = the shared cross-tenant
  `a30a87ed25634629aa6c3958aa2b91ea`. Combined filter confirmed
  2026-09-25: 17 jobs.
- `bulletFields` is single-element (`[reqId]`). The per-job family isn't in
  the list response, so `category` is a combined label for the three
  families. Location comes from the detail endpoint, since multi-location
  postings show a "3 Locations" placeholder in the list (same as Manulife).
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

# Opaque Workday facet IDs, confirmed against the tenant's own facet metadata.
CATEGORY_FACET_IDS = [
    "b18e449d87914e8db756066e35d5f247",  # IT - Application Development
    "fc46f3fb6ab24457be62e0b15c2c0101",  # IT - Technology Services
    "9d42de6b15aa0173c155daaa6201da7f",  # IT - Digital Development
]
COUNTRY_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"  # Canada


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Sun Life",
        base_url="https://sunlife.wd3.myworkdayjobs.com",
        tenant="sunlife",
        site="Experienced-Jobs",
        applied_facets={
            "jobFamily": CATEGORY_FACET_IDS,
            "Location_Country": [COUNTRY_FACET_ID],
        },
        category_label="IT",
    )
