"""TD careers scraper, scoped to Canada + Technology Solutions.

Same Workday CXS API approach as SOTI (scrapers/soti.py) — see that module's
docstring for how this pattern works in general. TD-specific notes:

- Tenant/site: `td.wd3.myworkdayjobs.com/TD_Bank_Careers`.
- Facet parameter names are `jobFamilyGroup` (Job Category) and
  `locationCountry` (nested under a `locationMainGroup` facet group in the
  site's facet metadata), confirmed: `jobFamilyGroup` value
  `de769652963501f2001247b507040dac` = "Technology Solutions",
  `locationCountry` value `a30a87ed25634629aa6c3958aa2b91ea` = "Canada" —
  the same opaque Canada ID seen on SOTI and CIBC.
- Unlike SOTI/CIBC, `bulletFields` here is `[reqId, jobFamily]` — TD's
  career site is configured to show a second, more specific field per job:
  its "Job Family" (a finer-grained sub-category under "Job Category", e.g.
  "Engineering", "Business Systems Analysis" — confirmed these values exist
  in the site's own `jobFamily` facet). Used as `category` directly instead
  of hardcoding the coarser "Technology Solutions" filter label, since it's
  real per-job data from the source.
- Posted date and canonical apply URL: same as SOTI, from each job's detail
  endpoint (`jobPostingInfo.startDate` / `.externalUrl`).
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

# Opaque Workday facet IDs, not derivable from their labels — confirmed
# against the site's own facet metadata (see module docstring).
CATEGORY_FACET_ID = "de769652963501f2001247b507040dac"  # Technology Solutions
COUNTRY_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"  # Canada


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="TD",
        base_url="https://td.wd3.myworkdayjobs.com",
        tenant="td",
        site="TD_Bank_Careers",
        applied_facets={"jobFamilyGroup": [CATEGORY_FACET_ID], "locationCountry": [COUNTRY_FACET_ID]},
        category_label="Technology Solutions",
        category_fn=_job_family,
    )


def _job_family(raw: dict, _detail: dict) -> str | None:
    bullet_fields = raw.get("bulletFields") or []
    return bullet_fields[1] if len(bullet_fields) > 1 else None
