"""IBM careers scraper (Canada / Software Engineering, plus data roles).

Job *discovery* goes through IBM's own custom Elasticsearch-backed search
index at www-api.ibm.com, not through IBM's actual application system of
record (Avature — see the module-level `platform` note below). This is a
public, unauthenticated POST endpoint that hands raw Elasticsearch query DSL
straight to the client, confirmed working with plain httpx (no browser, no
bot-blocking). See CLAUDE.md's "Meta, Amazon, Google, Apple, Microsoft, IBM,
Canonical scraping approach" section (IBM bullet) for how the endpoint itself
was found; the exact request-body shape below was confirmed live on
2026-09-21 since CLAUDE.md's summary didn't spell it out completely.

- Endpoint: `POST https://www-api.ibm.com/search/api/v2`.
- The body needs `appId: "careers"` and `scopes: ["careers2"]` (found
  embedded in careers.ibm.com/careers/search's page JS as
  `careerSearchAppId = {appid: 'careers'}` / `careerSearchScope = {scopeid:
  'careers2'}`) — omitting either 400s with "Either 'scopes' or
  'adopterdoctypes' is required".
- The `query` field is passed *directly* as Elasticsearch Query DSL (not
  wrapped in an extra `{"query": {...}}` layer, and NOT using `post_filter`
  as a nested key under `query` — that 400s with "unknown query
  [post_filter]"). A plain `{"bool": {"must": [...]}}` under `query` works
  directly and returns real hits.
- Confirmed working filter terms (matches CLAUDE.md exactly):
  `{"term": {"field_keyword_08": "Software Engineering"}}` and
  `{"term": {"field_keyword_05": "Canada"}}`, both inside `query.bool.must`.
- Only the Canada term is sent now: Canada has few postings (62 on
  2026-11-02), so they're all read and scoped client-side to
  `field_keyword_08` (the category) of "Software Engineering" or "Data &
  Analytics", or a data title.
- `_source` must be an explicit list of field names, not `true`/`["*"]`
  (both 400 with "Invalid value") — `["title", "url", "description"]` works.
- Pagination: standard Elasticsearch `size`/`from` in the POST body. Only
  the first page's `hits.total.value` is trusted, per this project's
  established Workday `total` bug-fix convention (see CLAUDE.md's BMO/CIBC/TD
  section) — confirmed IBM's `total` stays consistent across pages here, but
  there's no reason to rely on that holding forever.
- **The default relevance sort isn't fully stable across the page boundary**
  (confirmed live: fetching `from=0,size=20` and `from=20,size=20` in two
  separate requests returned 2 of the same jobIds in both pages) — the same
  "most relevant sort isn't fully stable" caveat CLAUDE.md documents for
  RBC's Phenom pagination applies here too. Handled the same way: dedupe on
  `external_id` within a run, and the `(company_id, external_id)` upsert
  makes any missed overlap a functional no-op.
- Each hit's `_source.url` is the canonical job URL, e.g.
  `https://careers.ibm.com/careers/JobDetail?jobId=131275` — the numeric
  `jobId` query param is extracted and used as `external_id`.
- **No location field beyond the generic `field_keyword_05: "Canada"`
  filter value itself, and no posted-date field at all** (confirmed live —
  requesting candidate field names like `location`/`primaryLocation`/
  `postedDate`/`date` in `_source` returns nothing for them). `location` is
  therefore hardcoded to "Canada" (already accurate, since every result is
  filtered to it) and `posted_date` is left `None` — the UI's fallback to
  `first_seen_at` (CLAUDE.md's "Posted date fallback") is the sanctioned
  behavior here, not a workaround.
- `platform` = **`"Avature"`** — CLAUDE.md confirms Avature (not this
  Elasticsearch index) is IBM's real underlying application system of
  record for job postings, even though discovery happens through this
  separate IBM-owned search API.
"""

import logging
import re

import httpx

from .base import NormalizedJob, clean_description, is_core_title

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www-api.ibm.com/search/api/v2"
APP_ID = "careers"
SCOPE = "careers2"
CATEGORIES = {"Software Engineering", "Data & Analytics"}
LOCATION_LABEL = "Canada"

# Big enough for every Canadian posting in one page: the relevance sort
# shifts between requests, so paging 20 at a time missed 8 of 62 jobs
# (2026-11-02).
PAGE_SIZE = 100
MAX_PAGES = 50  # safety cap; this filter currently returns ~2 pages


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    total: int | None = None

    with httpx.Client(timeout=30) as client:
        for page in range(MAX_PAGES):
            offset = page * PAGE_SIZE
            response = client.post(
                SEARCH_URL,
                json={
                    "appId": APP_ID,
                    "scopes": [SCOPE],
                    "size": PAGE_SIZE,
                    "from": offset,
                    "_source": ["title", "url", "description", "field_keyword_08"],
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"field_keyword_05": LOCATION_LABEL}},
                            ]
                        }
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
            # Only trust `total` from the first page — same precaution as
            # the Workday scrapers, in case IBM's index ever behaves like
            # TD's Workday tenant did (see CLAUDE.md).
            if total is None:
                total = payload["hits"]["total"]["value"]
            hits = payload["hits"]["hits"]
            if not hits:
                break

            for hit in hits:
                job_id = _extract_job_id(hit)
                if job_id is None:
                    logger.warning("IBM: skipping hit id=%s — could not extract jobId from url", hit.get("_id"))
                    continue
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                source = hit["_source"]
                if source.get("field_keyword_08") in CATEGORIES or is_core_title(source["title"]):
                    jobs.append(_normalize(job_id, source))

            offset += PAGE_SIZE
            if offset >= total:
                break
        else:
            logger.warning("IBM scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("IBM: fetched %d jobs (site reported total=%s)", len(jobs), total)
    return jobs


def _extract_job_id(hit: dict) -> str | None:
    url = hit.get("_source", {}).get("url", "")
    match = re.search(r"[?&]jobId=(\d+)", url)
    return match.group(1) if match else None


def _normalize(job_id: str, raw: dict) -> NormalizedJob:
    return {
        "external_id": job_id,
        "title": raw["title"],
        "url": raw["url"],
        "location": LOCATION_LABEL,
        "category": raw.get("field_keyword_08") or "",
        "posted_date": None,
        "platform": "Avature",
        "description": clean_description(raw.get("description")),
    }
