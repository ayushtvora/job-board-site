"""Rogers careers scraper, scoped to Digital & Technology.

`jobs.rogers.com` is SAP SuccessFactors' Jobs2Web layer — same as
Scotiabank — via the shared helper in scrapers/jobs2web.py. The site's own
"Digital & Technology" (also linked as "Technology") category landing page
is `/go/Digital-&-Technology/9547900/` (21 jobs, 2026-09-25). A second
"Digital & Technology" link on the homepage, `/go/.../8824700/`, is stale
and redirects to an error page. Rogers is Canadian-only, so no country
filter is needed.
"""

from .base import NormalizedJob
from .jobs2web import scrape_jobs2web


def scrape() -> list[NormalizedJob]:
    return scrape_jobs2web(
        name="Rogers",
        base_url="https://jobs.rogers.com",
        category_path="/go/Digital-%26-Technology/9547900",
        category_label="Digital & Technology",
    )
