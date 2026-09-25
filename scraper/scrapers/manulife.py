"""Manulife careers scraper, scoped to Canada + Information Technology.

Scrapes Manulife's **Workday tenant directly**, not the public careers site
at careers.manulife.com. That site is a Phenom People front-end (same
platform as RBC/BMO), but it sits behind an Akamai WAF that returns an
immediate 403 to every automated client tried — plain HTTP, browser-like
headers, and a real headless Chromium, from several different networks
including the server this scraper runs on. It's an instant block page, not
a JS challenge, so there's nothing for a scraper to solve. See CLAUDE.md's
"Manulife scraping approach" section.

Workday is the system of record behind that front-end (as it is for RBC and
BMO, whose apply links also point at Workday), and its API is not behind the
WAF, so it's used as the source instead. Approach is otherwise identical to
the other Workday scrapers — see scrapers/soti.py's docstring.

Manulife-specific notes:

- Tenant/site: `manulife.wd3.myworkdayjobs.com/MFCJH_Jobs` (a combined
  Manulife/John Hancock careers site). The site ID isn't guessable; it was
  found from a real apply link to this tenant published on a job aggregator.
- Facet parameters are `jobFamilyGroup` (Job Category) and
  `Location_Country`, confirmed against the site's own facet metadata:
  `838ae04677e543c2a0a85dfd1cab030a` = "Information Technology Group",
  `a30a87ed25634629aa6c3958aa2b91ea` = "Canada" (the same shared Canada ID
  used by SOTI/CIBC/TD).
- `bulletFields` is `[reqId, city]` here — the second element is a location,
  not a category like TD's job family — so `category` is hardcoded to the
  filtered facet's label.
- **Location comes from the detail endpoint, not the listing.** Manulife has
  many multi-location postings, for which the listing's `locationsText` is a
  useless placeholder like "2 Locations" / "50 Locations". The detail
  endpoint's `jobPostingInfo.location` is always a real place name.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

# Opaque Workday facet IDs, not derivable from their labels — confirmed
# against the site's own facet metadata (see module docstring).
CATEGORY_FACET_ID = "838ae04677e543c2a0a85dfd1cab030a"  # Information Technology Group
COUNTRY_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"  # Canada


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Manulife",
        base_url="https://manulife.wd3.myworkdayjobs.com",
        tenant="manulife",
        site="MFCJH_Jobs",
        applied_facets={"jobFamilyGroup": [CATEGORY_FACET_ID], "Location_Country": [COUNTRY_FACET_ID]},
        category_label="Information Technology Group",
    )
