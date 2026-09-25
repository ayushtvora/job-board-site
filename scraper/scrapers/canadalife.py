"""Canada Life careers scraper, scoped to the Digital Technology department.

Canada Life's system of record is SAP SuccessFactors (classic RCM,
`career5.successfactors.eu`, company `thegreatweP2`), but its public job
list is the Jobs2Web layer at `jobs.canadalife.com` — linked from
careers.canadalife.com's "career streams" pages — via the shared helper in
scrapers/jobs2web.py.

- There's no Technology category landing page, only `/go/All-Jobs/9170201/`
  (92 jobs, 2026-09-25), but its table has a Department column, filtered
  client-side on "Digital Technology" (11 jobs).
- The classic RCM XML feed
  (`career5.successfactors.eu/career?company=thegreatweP2&career_ns=job_listing_summary&resultType=XML`)
  also works without a session, but only has title/req ID/posted date — no
  location or department — and isn't well-formed XML (custom fields render
  with empty tag names like `<>205</>`), so Jobs2Web is the better source.
"""

from .base import NormalizedJob
from .jobs2web import scrape_jobs2web

DEPARTMENTS = {"Digital Technology"}


def scrape() -> list[NormalizedJob]:
    return scrape_jobs2web(
        name="Canada Life",
        base_url="https://jobs.canadalife.com",
        category_path="/go/All-Jobs/9170201",
        category_label="Digital Technology",
        department_filter=DEPARTMENTS.__contains__,
    )
