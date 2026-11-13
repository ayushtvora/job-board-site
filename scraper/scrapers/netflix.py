"""Netflix careers scraper (Canada / technical roles).

jobs.netflix.com is Eightfold (`explore.jobs.netflix.net`), but the newer
`/api/pcsx/search` API that scrapers/eightfold.py uses answers "PCSX is not
enabled for this user" here. The older `/api/apply/v2/jobs` API (the one
Liberty Mutual uses) works without auth:
`GET https://explore.jobs.netflix.net/api/apply/v2/jobs?domain=netflix.com&location=Canada&start=N&num=10`.

- `location=Canada` narrows the set (34 of 469 on 2026-10-02) but also
  returns postings whose *other* locations are Canadian (e.g. "Los
  Angeles; Vancouver; Los Gatos"). Those are kept, and anything without a
  Canadian location is dropped client-side.
- The page size is fixed at 10 whatever `num` asks for.
- Netflix's Canadian postings are almost all Netflix Animation Studios in
  Vancouver, and `department` there is "Feature Animation" for artists and
  engineers alike. So scope is a title match (engineer, developer,
  technical director/supervisor, data, technology).
- Fields: `display_job_id` (e.g. "JR42454", external_id), `name`,
  `locations[]`, `department`, `t_create` (Unix timestamp),
  `canonicalPositionUrl`.
- It answers 429 now and then (failed the 6am runs on 2026-11-13 and the
  first request of a manual run on 11-10, fine otherwise), so a 429 is
  retried with exponential backoff, 30s doubling to 240s.
"""

import logging
import re
import time
from datetime import datetime, timezone

import httpx

from .base import CANADA_PATTERN, NormalizedJob, is_core_title

logger = logging.getLogger(__name__)

LIST_URL = "https://explore.jobs.netflix.net/api/apply/v2/jobs"
MAX_PAGES = 50
RATE_LIMIT_BACKOFF_SECONDS = tuple(30 * 2**attempt for attempt in range(4))
TITLE_PATTERN = re.compile(
    r"engineer|developer|software|technical director|technical supervisor|technology|data|machine learning|security",
    re.IGNORECASE,
)


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    start = 0
    total = 0

    with httpx.Client(timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as client:
        for _ in range(MAX_PAGES):
            response = _get(client, {"domain": "netflix.com", "location": "Canada", "start": start, "num": 10})
            payload = response.json()
            total = payload.get("count", 0)
            positions = payload.get("positions") or []
            if not positions:
                break
            for raw in positions:
                job_id = str(raw.get("display_job_id") or raw["id"])
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                canadian = [loc for loc in raw.get("locations") or [] if CANADA_PATTERN.search(loc)]
                if canadian and (TITLE_PATTERN.search(raw.get("name") or "") or is_core_title(raw.get("name") or "")):
                    jobs.append(_normalize(raw, job_id, canadian))
            start += len(positions)
            if start >= total:
                break
        else:
            logger.warning("Netflix scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Netflix: fetched %d matching jobs (of %d for location=Canada)", len(jobs), total)
    return jobs


def _get(client: httpx.Client, params: dict) -> httpx.Response:
    for wait in (*RATE_LIMIT_BACKOFF_SECONDS, None):
        response = client.get(LIST_URL, params=params)
        if response.status_code != 429 or wait is None:
            break
        logger.warning("Netflix: rate-limited (429), retrying in %ds", wait)
        time.sleep(wait)
    response.raise_for_status()
    return response


def _normalize(raw: dict, job_id: str, canadian_locations: list[str]) -> NormalizedJob:
    created = raw.get("t_create")
    return {
        "external_id": job_id,
        "title": raw["name"].strip(),
        "url": raw.get("canonicalPositionUrl") or f"https://explore.jobs.netflix.net/careers/job/{raw['id']}",
        "location": "; ".join(loc.replace(",", ", ") for loc in canadian_locations),
        "category": raw.get("department") or "",
        "posted_date": datetime.fromtimestamp(created, tz=timezone.utc).strftime("%Y-%m-%d") if created else None,
        "platform": "Eightfold",
    }
