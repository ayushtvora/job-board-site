"""Shared helper for Greenhouse Board API scrapers (the fourth wave onward).

Same API as the Airbnb/Databricks/Stripe/Reddit scrapers (see CLAUDE.md's
"Airbnb, Databricks, Stripe scraping approach"):

- `GET /v1/boards/<token>/jobs?content=true` returns every job in one call.
- `GET /v1/boards/<token>/departments` returns the department tree
  (`parent_id` links). Department filtering here matches a job if its
  department **or any ancestor** has a name in `departments` — so passing a
  parent like "Engineering" picks up all its sub-teams, and the filter
  survives Greenhouse adding new sub-teams later. `exclude_departments`
  removes sub-trees again (e.g. Design under an "EPD" parent).
- No server-side location filter; Canada is matched client-side on
  `location.name` *and* each office's name/location — several companies
  (Cloudflare, Faire) put the real city only in `offices`, with
  `location.name` being just "Hybrid"/"Distributed" or a US-only string.
- Greenhouse's own `id` is the `external_id` (`requisition_id` is
  unreliable — see the Stripe/Airbnb notes in CLAUDE.md), and
  `first_published` is the true original posting date.

Not used by the pre-existing Greenhouse scrapers, which predate it.
"""

import logging
from collections.abc import Callable

import httpx

from .base import CANADA_PATTERN, NormalizedJob

logger = logging.getLogger(__name__)


def scrape_greenhouse(
    *,
    name: str,
    board_token: str,
    departments: set[str],
    exclude_departments: set[str] = frozenset(),
    is_canada: Callable[[dict], bool] | None = None,
) -> list[NormalizedJob]:
    base = f"https://boards-api.greenhouse.io/v1/boards/{board_token}"
    with httpx.Client(timeout=60) as client:
        jobs_response = client.get(f"{base}/jobs", params={"content": "true"})
        jobs_response.raise_for_status()
        raw_jobs = jobs_response.json()["jobs"]
        dept_response = client.get(f"{base}/departments")
        dept_response.raise_for_status()
        dept_tree = {d["id"]: d for d in dept_response.json()["departments"]}

    canada_check = is_canada or default_is_canada
    matched = [
        raw
        for raw in raw_jobs
        if _in_departments(raw, dept_tree, departments, exclude_departments) and canada_check(raw)
    ]
    logger.info("%s: fetched %d matching jobs (of %d total)", name, len(matched), len(raw_jobs))
    return [_normalize(raw) for raw in matched]


def location_strings(raw: dict) -> list[str]:
    strings = [(raw.get("location") or {}).get("name") or ""]
    for office in raw.get("offices") or []:
        strings.append(office.get("name") or "")
        strings.append(office.get("location") or "")
    return strings


def default_is_canada(raw: dict) -> bool:
    return any(CANADA_PATTERN.search(s) for s in location_strings(raw))


def _ancestor_names(dept_id: int, dept_tree: dict) -> list[str]:
    names = []
    seen = set()
    while dept_id in dept_tree and dept_id not in seen:
        seen.add(dept_id)
        dept = dept_tree[dept_id]
        names.append(dept["name"].strip())
        dept_id = dept.get("parent_id")
    return names


def _in_departments(raw: dict, dept_tree: dict, include: set[str], exclude: set[str]) -> bool:
    for dept in raw.get("departments") or []:
        chain = _ancestor_names(dept["id"], dept_tree) or [dept["name"].strip()]
        if any(n in exclude for n in chain):
            continue
        if any(n in include for n in chain):
            return True
    return False


def _normalize(raw: dict) -> NormalizedJob:
    location = (raw.get("location") or {}).get("name") or ""
    offices = [o["name"] for o in raw.get("offices") or [] if o.get("name")]
    # Some boards put only "Hybrid"/"Distributed" in location.name — append
    # the office names so the displayed location is an actual place.
    if offices and not CANADA_PATTERN.search(location):
        location = f"{location} ({'; '.join(offices)})" if location else "; ".join(offices)
    posted_date = raw.get("first_published")
    return {
        "external_id": str(raw["id"]),
        "title": raw["title"].strip(),
        "url": raw["absolute_url"],
        "location": location,
        "category": ", ".join(d["name"].strip() for d in raw.get("departments") or []),
        "posted_date": posted_date[:10] if posted_date else None,
        "platform": "Greenhouse",
    }
