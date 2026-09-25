"""Scotiabank careers scraper (IT & Digital Banking Jobs category).

Runs on SAP SuccessFactors (Jobs2Web career site layer) — a fourth distinct
ATS (RBC/BMO use Phenom, SOTI/CIBC/TD use Workday, EA uses Avature). Plain
server-rendered HTML table, no session/JS required, parsed with
BeautifulSoup.

- The given URL (`/go/IT-&-Digital-Banking-Jobs/2298017/`) *is* the
  "Technology" filter — it's a category-specific landing page, not a
  generic search with query-string facets like the other scrapers. Only
  filter requested for Scotiabank is "Technology", with no country facet
  applied on top (unlike BMO/CIBC/TD), so this scrapes that page as-is,
  whatever countries it includes.
- **Pagination** is a URL path segment (not a query param), in steps of the
  page size (25): `.../2298017/0/`, `.../2298017/25/`, `.../2298017/50/`,
  etc. — confirmed `/0/` is equivalent to the bare category URL (both give
  "Page 1 of N"), so the loop can always include the offset uniformly.
- **Fields available per row**: title + detail URL (`.jobTitle-link`,
  numeric job ID as the URL's trailing path segment), a human-readable
  date (`.jobDate`, e.g. "Sep 18, 2026"), and location (`.jobLocation`,
  e.g. "Toronto, ON, CA, M5H1H1").
- No per-job category is shown (the whole page is already one category), so
  `category` is hardcoded to this page's own label, same reasoning as the
  Workday scrapers' category facet.
- **`platform` = `"SuccessFactors"`** for Scotiabank.
"""

from .base import NormalizedJob
from .jobs2web import scrape_jobs2web


def scrape() -> list[NormalizedJob]:
    return scrape_jobs2web(
        name="Scotiabank",
        base_url="https://jobs.scotiabank.com",
        category_path="/go/IT-%26-Digital-Banking-Jobs/2298017",
        category_label="IT & Digital Banking Jobs",
    )
