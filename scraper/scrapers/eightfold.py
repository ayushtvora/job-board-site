"""Shared helper for Eightfold career-site scrapers (the `pcsx` search API).

Same API as Microsoft and Autodesk (see CLAUDE.md's "Microsoft scraping
approach" and the Autodesk notes): the client-rendered careers SPA calls
`GET <base_url>/api/pcsx/search?domain=<domain>&query=&location=<text>&start=<offset>`,
found via a Playwright network capture. `location` is free text (no opaque
facet IDs); `start` is an offset, and the page size is fixed by the server
(10 at Microsoft), so paging advances by however many came back and stops
once a page adds no new IDs. Response shape is `{"data": {"positions": [...]}}`.

- Tenants differ in which facets work: Microsoft's `department=` param is
  silently ignored (filter client-side with `job_filter`), while Autodesk's
  repeatable `filter_job_category=` works (pass it in `extra_params`).
- Data roles: Canadian jobs with a data title are kept whatever
  `job_filter` says. Tenants that filter by category in `extra_params`
  also get a keyword search (`query=<term>`) for each of
  `DATA_SEARCH_TERMS`, which is sorted by relevance, so paging stops at
  the first page without a data title.
- `external_id` is the human req number (`displayJobId`, else `atsJobId`),
  falling back to Eightfold's own `id`.
- `postedTs` is a Unix timestamp but is 0 on some tenants (Autodesk), so
  `creationTs` is the fallback.
- Postings can list many locations; Canadian ones are shown first, up to
  three, with a count of the rest.
- Microsoft and Qualcomm sometimes answer the very first request with 429
  during the 6am run (seen 2026-09-30 and 2026-10-02) while manual runs
  later in the day succeed, so a 429 is retried after a wait (`Retry-After`
  if it's given in seconds, else 30s/60s/120s) before giving up.

Liberty Mutual's older Eightfold `/api/apply/v2/jobs` API has different
field names and isn't covered here (see scrapers/libertymutual.py).
"""

import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone

import httpx

from .base import CANADA_PATTERN, DATA_SEARCH_TERMS, NormalizedJob, is_data_title

logger = logging.getLogger(__name__)

MAX_PAGES = 50
MAX_LOCATIONS_SHOWN = 3
RATE_LIMIT_BACKOFF_SECONDS = (30, 60, 120)
MAX_RETRY_AFTER_SECONDS = 300
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept": "application/json",
}


def scrape_eightfold(
    *,
    name: str,
    base_url: str,
    domain: str,
    location: str = "Canada",
    extra_params: list[tuple[str, str]] = (),
    category_label: str | None = None,
    job_filter: Callable[[dict], bool] | None = None,
) -> list[NormalizedJob]:
    """`category_label` overrides the per-job `department` as the category
    (for tenants where `department` isn't meaningful). `job_filter(raw)` can
    narrow the scope client-side; Canadian jobs with a data title skip it."""
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()

    def is_canadian_data(raw: dict) -> bool:
        locations = raw.get("locations") or []
        if isinstance(locations, str):
            locations = [locations]
        return is_data_title(raw.get("name") or "") and any(CANADA_PATTERN.search(loc) for loc in locations)

    with httpx.Client(timeout=30, headers=HEADERS) as client:

        def scrape_pass(query: str, pass_params: list[tuple[str, str]], data_only: bool) -> None:
            start = 0
            for _ in range(MAX_PAGES):
                params = [("domain", domain), ("query", query), ("location", location), ("start", str(start)), *pass_params]
                response = _get(client, f"{base_url}/api/pcsx/search", params, name)
                postings = (response.json().get("data") or {}).get("positions") or []
                if not postings:
                    break
                new_on_page = 0
                for raw in postings:
                    job_id = str(raw.get("displayJobId") or raw.get("atsJobId") or raw["id"])
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)
                    new_on_page += 1
                    keep = is_canadian_data(raw) if data_only else (job_filter is None or job_filter(raw) or is_canadian_data(raw))
                    if keep:
                        jobs.append(_normalize(raw, job_id, base_url, category_label))
                if new_on_page == 0 or (data_only and not any(is_data_title(raw.get("name") or "") for raw in postings)):
                    break
                start += len(postings)
            else:
                logger.warning("%s scrape hit MAX_PAGES=%d without finishing — got %d jobs", name, MAX_PAGES, len(jobs))

        scrape_pass("", list(extra_params), data_only=False)
        # Category params leave out data roles in other categories, so those
        # come from a keyword search. Without them the first pass already
        # saw every job for `location`.
        if extra_params:
            for term in DATA_SEARCH_TERMS:
                scrape_pass(term, [], data_only=True)

    logger.info("%s: fetched %d jobs", name, len(jobs))
    return jobs


def _get(client: httpx.Client, url: str, params: list[tuple[str, str]], name: str) -> httpx.Response:
    for backoff in RATE_LIMIT_BACKOFF_SECONDS:
        response = client.get(url, params=params)
        if response.status_code != 429:
            break
        retry_after = response.headers.get("Retry-After", "")
        wait = min(int(retry_after), MAX_RETRY_AFTER_SECONDS) if retry_after.isdigit() else backoff
        logger.warning("%s: rate-limited (429), retrying in %ds", name, wait)
        time.sleep(wait)
    else:
        response = client.get(url, params=params)
    response.raise_for_status()
    return response


def _normalize(raw: dict, job_id: str, base_url: str, category_label: str | None) -> NormalizedJob:
    locations = raw.get("locations") or []
    if isinstance(locations, str):
        locations = [locations]
    canadian = [loc for loc in locations if CANADA_PATTERN.search(loc)] or locations
    location = "; ".join(canadian[:MAX_LOCATIONS_SHOWN])
    if len(canadian) > MAX_LOCATIONS_SHOWN:
        location += f" (+{len(canadian) - MAX_LOCATIONS_SHOWN} more)"

    timestamp = raw.get("postedTs") or raw.get("creationTs")
    position_url = raw.get("positionUrl") or f"/careers/job/{raw['id']}"
    return {
        "external_id": job_id,
        "title": (raw.get("name") or "").strip(),
        "url": position_url if position_url.startswith("http") else f"{base_url}{position_url}",
        "location": location,
        "category": category_label or raw.get("department") or "",
        "posted_date": datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d") if timestamp else None,
        "platform": "Eightfold",
    }
