"""BMO careers scraper (Technology category).

Same Phenom People platform as RBC (scrapers/rbc.py) — job data for each
page of results is embedded server-side in a `phApp.ddo = {...}` JSON
blob, so a plain HTTP GET is enough, no browser needed. See rbc.py's
docstring for the general shape of this approach.

BMO-specific notes:

- The `/ca/en/` site section is Canada-only already (confirmed: the site's
  own `country` facet reports 100% "Canada" across all 597 unfiltered
  jobs), so no separate country filter is needed to satisfy "Country:
  Canada" — unlike RBC, which has no such per-country split.
- Category filtering is a plain human-readable query param,
  `?category=Technology` — matches the `category` facet's label exactly
  (confirmed: filtering drops totalHits from 597 to 63, matching that
  facet's own reported count). No opaque ID involved, unlike Workday's
  facets.
- **Pagination quirk**: RBC's `&s=1` pagination param, when combined with
  `category=...` here, silently drops the category filter entirely (reverts
  to the full unfiltered 597). Omitting `s` and paginating with `from=N`
  alone works correctly with the filter applied (confirmed jobs on
  paginated pages are all distinct `Technology` jobs) — so BMO's scraper
  deliberately does NOT send `s`, unlike RBC's.
- Same per-job fields as RBC's blob: `jobId`, `title`, `postedDate`,
  `category`, `location`, `applyUrl` (`*.wd3.myworkdayjobs.com` for every
  job seen). **`platform` = `"Workday"`** for BMO, same as RBC.
"""

from .base import NormalizedJob
from .phenom import scrape_phenom


def scrape() -> list[NormalizedJob]:
    return scrape_phenom(
        name="BMO",
        list_url="https://jobs.bmo.com/ca/en/search-results",
        categories=["Technology"],
        platform="Workday",
    )
