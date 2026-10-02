"""Meta careers scraper (Canada / Software Engineering jobs).

Unlike every other scraper in this project, Meta cannot be scraped with a
lightweight `httpx` request. `metacareers.com` returns HTTP 400 to plain
curl/httpx regardless of headers sent — a TLS/HTTP2 client-fingerprint-level
block, not a WAF challenge page — but a real or headless Chromium passes
through fine. The real data comes back from `POST
https://www.metacareers.com/graphql`, but that request body carries roughly
ten Meta-internal anti-automation tokens (`lsd`, `jazoest`, `__hs`, `__dyn`,
`__csr`, `__rev`, `__spin_r`, ...) minted by the page's own JS at load time —
session-bound values, not hardcodable secrets — so the POST can't be forged
directly. See CLAUDE.md's "Meta, Amazon, Google, Apple, Microsoft, IBM,
Canonical scraping approach" section (Meta bullet) for the original
investigation this builds on, and the notes below for what was reconfirmed
live on 2026-09-21.

Approach: launch a headless Chromium via Playwright, navigate directly to
the jobs search page with the desired filters baked into the URL as query
params, and intercept the GraphQL response the page fires on load — rather
than trying to reconstruct the POST body ourselves.

Live-reconfirmed details (2026-09-21), refining CLAUDE.md's investigation:

- **Deep-linking works.** Navigating straight to
  `metacareers.com/jobs?teams[0]=Software%20Engineering&offices[0]=montreal&...`
  causes the page's own initial `CareersJobSearchResultsV2DataQuery` GraphQL
  call to already reflect those filters (confirmed via the `variables` in
  the request body) — no need to drive the filter UI by hand.
- **`offices` takes location *IDs*, not country names.** Passing
  `offices[0]=Canada` looks plausible but silently matches nothing (Meta's
  location facet is per-city, not per-country, as CLAUDE.md already noted).
  The 6 Canada location IDs CLAUDE.md listed were reconfirmed live against
  the `CareersJobSearchLocationFilterV3Query` facet response, which reports
  each one's `country` field: `montreal`, `toronto`, `vancouver`, `ottawa`,
  `canada-remote`, `sturgeon-county-dc`. All 6 are passed together as
  `offices[]`.
- **`teams` takes the display name directly** (e.g. `"Software
  Engineering"`), confirmed against `CareersJobSearchFiltersV3Query`'s facet
  list — no opaque ID for this facet.
- **Response shape**: `data.job_search_with_featured_jobs_v2` has two
  separate lists — `all_jobs` (the actual filtered search results) and
  `featured_jobs` (unrelated global promoted postings that ignore the
  filters entirely — confirmed live: with Canada+Software Engineering
  applied, `featured_jobs` still returned an unrelated US-only Data Center
  role). Only `all_jobs` is used here.
- **No pagination needed in practice.** `search_input.results_per_page` is
  `null` by default and the site does not appear to cap results at a fixed
  page size: an unfiltered `teams=["Software Engineering"]` query (no
  location filter) returned all 85 matching jobs in the single response,
  matching CLAUDE.md's note that a fully unfiltered query once returned all
  989 company-wide jobs in one shot. Since the Canada-scoped result set is
  much smaller still, no follow-up "next page" request is implemented — if
  a future result count lands suspiciously on a round number (25/50/100),
  that would be a sign a page cap has since been introduced and this needs
  revisiting.
- **Job detail URL**: `https://www.metacareers.com/jobs/<id>/` 301-redirects
  to `https://www.metacareers.com/profile/job_details/<id>/`, confirmed to
  render the correct job (live-verified for a real job ID). The `/jobs/<id>/`
  form is used as the stored `url` since it's simpler and permanently
  redirects.
- **No posted-date field anywhere** in the search response (only `id`,
  `title`, `locations`, `teams`, `sub_teams`) — `posted_date` is left `None`,
  per CLAUDE.md; the UI's `first_seen_at` fallback handles display.
- `category` is set to the job's own `teams` (joined), not hardcoded to
  "Software Engineering" — since every result is already scoped to that
  team by the query, but some jobs carry additional real teams (e.g.
  "Software Engineering, University Grad - Engineering, Tech & Design,
  Research" was seen live), which is more informative than a fixed label.

Playwright and Chromium are installed by requirements.txt and the
Dockerfile (scrapers/uber.py is the only other scraper that needs them).
"""

import logging
import urllib.parse

from playwright.sync_api import sync_playwright

from .base import NormalizedJob

logger = logging.getLogger(__name__)

TEAM = "Software Engineering"
CANADA_OFFICE_IDS = [
    "montreal",
    "toronto",
    "vancouver",
    "ottawa",
    "canada-remote",
    "sturgeon-county-dc",
]

GRAPHQL_FRIENDLY_NAME = "CareersJobSearchResultsV2DataQuery"
PLATFORM = "Meta Careers (custom, in-house)"

NAV_TIMEOUT_MS = 45_000
RESPONSE_TIMEOUT_MS = 30_000


def _search_url() -> str:
    params = [("teams[0]", TEAM)]
    params += [(f"offices[{i}]", office_id) for i, office_id in enumerate(CANADA_OFFICE_IDS)]
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"https://www.metacareers.com/jobs?{query}"


def _is_search_response(response) -> bool:
    if "graphql" not in response.url:
        return False
    post_data = response.request.post_data or ""
    return GRAPHQL_FRIENDLY_NAME in post_data


def scrape() -> list[NormalizedJob]:
    url = _search_url()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            with page.expect_response(_is_search_response, timeout=RESPONSE_TIMEOUT_MS) as response_info:
                page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            response = response_info.value
            if response.status != 200:
                raise ValueError(f"Meta GraphQL search returned HTTP {response.status}")
            payload = response.json()
        finally:
            browser.close()

    if "errors" in payload:
        raise ValueError(f"Meta GraphQL search returned errors: {payload['errors']}")

    raw_jobs = payload["data"]["job_search_with_featured_jobs_v2"]["all_jobs"]

    jobs: list[NormalizedJob] = [_normalize(raw) for raw in raw_jobs]

    logger.info("Meta: fetched %d jobs (Canada + %s)", len(jobs), TEAM)
    return jobs


def _normalize(raw: dict) -> NormalizedJob:
    job_id = raw["id"]
    return {
        "external_id": job_id,
        "title": raw["title"],
        "url": f"https://www.metacareers.com/jobs/{job_id}/",
        "location": ", ".join(raw.get("locations", [])),
        "category": ", ".join(raw.get("teams", [])) or TEAM,
        "posted_date": None,  # Meta's search API exposes no posted-date field.
        "platform": PLATFORM,
    }
