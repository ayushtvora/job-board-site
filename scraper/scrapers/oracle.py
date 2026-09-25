"""Oracle (the corporation) careers scraper — Product and Research jobs.

Oracle's own careers site (careers.oracle.com) runs on Oracle Recruiting
Cloud (Fusion Cloud HCM), not a third-party ATS. It exposes a public,
unauthenticated REST API (found via the CSP header on the marketing page)
— no browser/session needed, plain HTTP GETs are enough. See CLAUDE.md's
"Intel, Oracle, Spotify, Adobe, Sony, AMD, Uber scraping approach" section
(Oracle bullet) for how this was found.

- Category filter: `selectedCategoriesFacet=<id>` — "Product and Research"
  = 302958497961752 (confirmed: narrows a global ~758-total unfiltered
  count to this category's own count).
- Canada filtering is fuzzy, not exact: confirmed the Canada location facet
  (`selectedLocationsFacet=300000000106749`) applied *together* with the
  category facet returns a small candidate set, but some entries have
  `PrimaryLocation` like "United States" (a real data quirk on Oracle's own
  site, not a bug here) — so the candidate set is filtered again
  client-side on `PrimaryLocation` containing "Canada".
- `JobFamily`/`JobFunction` are null at this site number (`CX_1`) — not
  used.
- The response shape is `{"items": [{... "requisitionList": [...],
  "TotalJobsCount": N, ...}], ...}` — one search-result object per call,
  confirmed live; `TotalJobsCount` reflects only the first page's query, so
  (per the existing TD-bug-fix convention used elsewhere in this scraper
  suite) it's only trusted from the first page.
"""

from .base import NormalizedJob
from .oracle_recruiting import scrape_oracle_recruiting

CATEGORY_FACET_ID = "302958497961752"  # "Product and Research"
LOCATION_FACET_ID = "300000000106749"  # "Canada" (fuzzy — see module docstring)


def scrape() -> list[NormalizedJob]:
    return scrape_oracle_recruiting(
        name="Oracle",
        host="eeho.fa.us2.oraclecloud.com",
        finder_filters={
            "selectedCategoriesFacet": CATEGORY_FACET_ID,
            "selectedLocationsFacet": LOCATION_FACET_ID,
        },
        page_size=20,
        category_label="Product and Research",
        # The location facet is fuzzy and also returns some US jobs.
        job_filter=lambda raw: "canada" in (raw.get("PrimaryLocation") or "").lower(),
    )
