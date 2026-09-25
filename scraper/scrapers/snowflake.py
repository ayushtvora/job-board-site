"""Snowflake careers scraper (Engineering category, Canada only).

Same Phenom People platform as RBC/BMO (scrapers/rbc.py, scrapers/bmo.py) —
job data is embedded server-side in a `phApp.ddo = {...}` JSON blob, so a
plain HTTP GET is enough, no browser needed. See rbc.py's docstring for the
general shape of this approach.

Snowflake-specific notes (see CLAUDE.md's "Snowflake scraping approach"
section):

- The job list lives at `ddo["eagerLoadRefineSearch"]["data"]["jobs"]` —
  confirmed live 2026-09-21 this is the *same* path RBC/BMO use (CLAUDE.md's
  note calling it "a different path than RBC's" doesn't hold up against the
  live blob; documenting the discrepancy here rather than re-guessing).
- Category filtering is `?category=Engineering` (confirmed against the
  blob's own totalHits, currently 95).
- Pagination: `from=<offset>` in steps of 10, no `s` param needed — same
  convention as RBC (not BMO's category-drops-with-`s` quirk; not tested
  with `s` here since omitting it already works cleanly).
- **No working country-level filter** — Canada jobs are found by fetching
  the category-filtered pages and filtering client-side on each job's own
  `country` field (plain country name, e.g. `"Canada"`).
- **No `jobId` field in this tenant's blob** (unlike RBC/BMO/Blizzard/Adobe)
  — the stable per-job identifier here is `reqId` (e.g. `"REQ18507"` or
  `"ASHREQ-7477"`), used as `external_id`.
- Every job's `applyUrl` points at `jobs.ashbyhq.com/snowflake/<uuid>` with
  `externalApply: true` — Snowflake's real underlying ATS is **Ashby**, not
  Workday (the Phenom front-end is purely a listing/branding layer, same
  relationship pattern as RBC/BMO/Manulife's Phenom-front/other-ATS-apply).
  `platform` = `"Ashby"`.
"""

from .base import NormalizedJob
from .phenom import scrape_phenom


def scrape() -> list[NormalizedJob]:
    return scrape_phenom(
        name="Snowflake",
        list_url="https://careers.snowflake.com/us/en/search-results",
        categories=["Engineering"],
        id_field="reqId",
        platform="Ashby",
        job_filter=lambda raw: raw.get("country") == "Canada",
    )
