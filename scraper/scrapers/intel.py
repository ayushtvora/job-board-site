"""Intel careers scraper, scoped to Canada + Software Engineering.

Same Workday CXS API approach as SOTI (scrapers/soti.py) — see that module's
docstring for how this pattern works in general. Intel-specific notes:

- The marketing-facing `jobs.intel.com` domain is dead (redirect loop); the
  real backend is Workday, tenant `intel.wd1.myworkdayjobs.com/External`.
- Category facet is `jobFamilyGroup`, value
  `ace7a3d23b7e01a0544279031a0ec85c` = "Software Engineering".
- **No single country-level facet exists** — locations are city-granular,
  nested as a `locations` facet under a `locationMainGroup` facet group in
  the site's facet metadata (confirmed by walking the metadata tree; the
  `appliedFacets` key to actually submit is the nested facet's own
  parameter name, `locations`, same as how TD's `locationCountry` is nested
  under `locationMainGroup` in its metadata but still submitted as a flat
  top-level key). Canada requires passing **both** `"Canada, Toronto"`
  (`1e4a4eb3adf1019f4237e975bf81b3ce`) and `"Virtual Canada"`
  (`3d7e019f2bb20100b6accdbea05c0000`) in that one list — confirmed
  Toronto-only gives 0 results, both together gives 3 (all "Virtual
  Canada"), matching this combined category+location filter exactly.
- `bulletFields` is single-element (`[reqId]`) for jobs matching this
  filter — `category` is hardcoded to the filtered facet's label, same
  reasoning as SOTI. (Note: some *other* Intel postings outside this filter
  have been seen with a non-ID first bulletField like "Spotlight Job", but
  none of the 3 real matches for this filter do — `bulletFields[0]` is safe
  here.)
- Posted date and canonical apply URL: same as SOTI, from each job's detail
  endpoint (`jobPostingInfo.startDate` / `.externalUrl`).
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

# Opaque Workday facet IDs, not derivable from their labels — confirmed
# against the site's own facet metadata (see module docstring).
CATEGORY_FACET_ID = "ace7a3d23b7e01a0544279031a0ec85c"  # Software Engineering
LOCATION_FACET_IDS = [
    "1e4a4eb3adf1019f4237e975bf81b3ce",  # Canada, Toronto
    "3d7e019f2bb20100b6accdbea05c0000",  # Virtual Canada
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Intel",
        base_url="https://intel.wd1.myworkdayjobs.com",
        tenant="intel",
        site="External",
        applied_facets={"jobFamilyGroup": [CATEGORY_FACET_ID], "locations": LOCATION_FACET_IDS},
        category_label="Software Engineering",
    )
