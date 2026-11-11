"""D-Wave careers scraper (Canada, software/data titles and IT departments).

D-Wave's careers page (dwavequantum.com/company/careers) embeds a
**Rippling** ATS board, `ats.rippling.com/d-wave-quantum/jobs`. Rippling's
public board API returns every posting in one call, no auth:
`GET https://api.rippling.com/platform/api/ats/v1/board/d-wave-quantum/jobs`
-> `[{uuid, name, department: {label}, url, workLocation: {label}}]`.
Investigated 2026-11-10: 56 postings, ~17 in Canada (Burnaby HQ,
"Hybrid (Burnaby, British Columbia, CA)", "Canada").

- No server-side filtering, so Canada is matched on `workLocation.label`.
- Departments are broad ("Research and Development" covers both quantum
  hardware physicists and software developers), so scope is by title
  (`base.is_core_title`) plus the IT and software departments.
- A posting with several locations is listed once per location under the
  same uuid, so locations are merged per uuid.
- Titles end in an internal requisition number ("... [639]"), which is
  stripped. No posted date; descriptions come from descriptions.py.
"""

import logging
import re

import httpx

from .base import CANADA_PATTERN, NormalizedJob, is_core_title

logger = logging.getLogger(__name__)

API_URL = "https://api.rippling.com/platform/api/ats/v1/board/d-wave-quantum/jobs"
TECH_DEPARTMENT_PATTERN = re.compile(r"software|information technology|\bIT\b|data", re.IGNORECASE)
REQ_SUFFIX_RE = re.compile(r"\s*\[\d+\]\s*$")


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=30) as client:
        response = client.get(API_URL)
        response.raise_for_status()
        postings = response.json()

    # A multi-location posting is listed once per location, same uuid.
    locations: dict[str, list[str]] = {}
    for raw in postings:
        label = (raw.get("workLocation") or {}).get("label") or ""
        locations.setdefault(raw["uuid"], [])
        if label and label not in locations[raw["uuid"]]:
            locations[raw["uuid"]].append(label)

    jobs: dict[str, NormalizedJob] = {}
    for raw in postings:
        title = REQ_SUFFIX_RE.sub("", raw["name"]).strip()
        location = "; ".join(locations[raw["uuid"]])
        department = (raw.get("department") or {}).get("label") or ""
        if raw["uuid"] in jobs or not CANADA_PATTERN.search(location):
            continue
        if not (is_core_title(title) or TECH_DEPARTMENT_PATTERN.search(department)):
            continue
        jobs[raw["uuid"]] = (
            {
                "external_id": raw["uuid"],
                "title": title,
                "url": raw["url"],
                "location": location,
                "category": department,
                "posted_date": None,
                "platform": "Rippling",
            }
        )
    logger.info("D-Wave: fetched %d matching jobs (of %d postings)", len(jobs), len(locations))
    return list(jobs.values())
