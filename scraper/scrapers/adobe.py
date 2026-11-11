"""Adobe careers scraper (Engineering and Product, Information Technology
and Research categories, Canada only).

Adobe had only 3 Canadian postings on 2026-11-10, one of them an IT-category
"Customer Success Engineer", so the IT and Research categories were added
then.

Same Phenom People platform as RBC/BMO (scrapers/rbc.py, scrapers/bmo.py) —
job data is embedded server-side in a `phApp.ddo = {...}` JSON blob, so a
plain HTTP GET is enough, no browser needed. See rbc.py's docstring for the
general shape of this approach.

Adobe-specific notes (see CLAUDE.md's "Intel, Oracle, Spotify, Adobe, Sony,
AMD, Uber scraping approach" section):

- Category filtering is `?category=Engineering and Product` (confirmed
  against the blob's own `category` facet aggregation: exactly matches that
  facet's reported count).
- **Has BMO's pagination quirk, not RBC's**: combining the `category=`
  param with `s=1` silently drops the filter back to the full unfiltered
  set (confirmed live — `s=1` returns the same totalHits as no category at
  all). Omitting `s` and paginating with `from=N` alone works correctly
  (confirmed jobs on paginated pages all carry "Engineering and Product" in
  their `multi_category` array) — so, like bmo.py, this scraper does NOT
  send `s`.
- A job's own `category` field can show a *different* primary category
  (e.g. "Design") even when it matched the "Engineering and Product" filter
  via its `multi_category` array (Adobe jobs can belong to multiple
  categories). `category` is still recorded as-is from the job's own field,
  same convention as every other scraper here (no cross-company
  normalization).
- **No working country query param** — every variant tried returns the
  unfiltered set. Canada jobs are found by fetching the category-filtered
  pages and filtering client-side on each job's own `country` field (full
  name string, e.g. `"Canada"`, `"United States of America"`).
- Every job's `applyUrl` points at `adobe.wd5.myworkdayjobs.com` — same
  Phenom-front/Workday-apply relationship as RBC/BMO. `platform` =
  `"Workday"`.
"""

from .base import NormalizedJob
from .phenom import scrape_phenom


def scrape() -> list[NormalizedJob]:
    return scrape_phenom(
        name="Adobe",
        list_url="https://careers.adobe.com/us/en/search-results",
        categories=["Engineering and Product", "Information Technology", "Research"],
        platform="Workday",
        job_filter=lambda raw: raw.get("country") == "Canada",
    )
