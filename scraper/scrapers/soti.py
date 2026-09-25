"""SOTI careers scraper, scoped to Mississauga HQ + Product Development.

SOTI's careers site runs on Workday directly (unlike RBC's Phenom People
site), which exposes a documented CXS JSON API — no HTML scraping needed.
See CLAUDE.md's "SOTI scraping approach" section for how this was found.

- List endpoint (POST .../wday/cxs/soti/Careers/jobs) takes an `appliedFacets`
  dict keyed by Workday facet parameter names; the values are the same
  opaque facet IDs that appear as query params on the site's own filtered
  URLs (e.g. `locations=<id>`).
- The list endpoint does not return a category, or an exact posted date, per
  job — only a relative string like "Posted 18 Days Ago". Since this scraper
  filters to one fixed category facet, every job it returns is by definition
  that category, so `category` is hardcoded to its label rather than read
  per-job.
- For an exact `posted_date` (and the canonical apply URL), each job's
  detail endpoint (GET .../wday/cxs/soti/Careers<externalPath>) is fetched;
  its `jobPostingInfo.startDate` is a plain ISO date — confirmed this
  matches the list's relative "Posted N Days Ago" text exactly (e.g. 18
  days before the date this was checked).
- `bulletFields[0]` in the list response is the job requisition ID (e.g.
  "R09972") and matches the detail endpoint's `jobReqId`, which the shared
  helper (scrapers/workday_cxs.py) uses as `external_id`.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

# Opaque Workday facet IDs, not derivable from their labels — confirmed
# against the site's own facet metadata (see module docstring).
LOCATION_FACET_ID = "023f9d25c4c11000bbfc52f5b4120000"  # Mississauga, Canada – Meadowvale Office (HQ)
CATEGORY_FACET_ID = "267bdbcbbd671001697698c0843a0001"  # Product Development


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="SOTI",
        base_url="https://soti.wd3.myworkdayjobs.com",
        tenant="soti",
        site="Careers",
        applied_facets={
            "locations": [LOCATION_FACET_ID],
            "EEB_-_Job_Categories_for_External_Site_Extended": [CATEGORY_FACET_ID],
        },
        category_label="Product Development",
    )
