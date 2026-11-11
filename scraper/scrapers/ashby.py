"""Shared helper for Ashby public job-board API scrapers.

`GET https://api.ashbyhq.com/posting-api/job-board/<org>` is Ashby's
public, unauthenticated posting API — returns every listed job in one call
(no pagination), each with `id` (stable UUID, used as `external_id`),
`title`, `department`, `team`, `location`, `secondaryLocations[]`,
`address.postalAddress.addressCountry`, `publishedAt` (real ISO datetime),
`jobUrl`, and `descriptionHtml`.

No server-side filtering, so Canada and department are matched client-side
(jobs with a core title (data, ML, software) are kept whatever their department):
Canada if the primary address or any secondary location's address has
`addressCountry == "Canada"`, or any location name mentions Canada.

Some orgs use `department` for a product area and put the discipline in
`team` (Hopper: "Travel Tech / Engineering"; Loopio: "Product / Product
Engineering"), so `departments=None` plus a `job_filter` can match on
anything in the raw posting instead.
"""

import logging
from collections.abc import Callable

import httpx

from .base import NormalizedJob, clean_description, is_core_title

logger = logging.getLogger(__name__)


def scrape_ashby(
    *,
    name: str,
    org: str,
    departments: set[str] | None,
    job_filter: Callable[[dict], bool] | None = None,
) -> list[NormalizedJob]:
    """`departments=None` skips department matching; `job_filter(raw)` can
    narrow the department scope client-side (core titles (data, ML, software) skip both)."""
    with httpx.Client(timeout=30) as client:
        response = client.get(f"https://api.ashbyhq.com/posting-api/job-board/{org}")
        response.raise_for_status()
        raw_jobs = response.json()["jobs"]

    matched = [
        raw
        for raw in raw_jobs
        if raw.get("isListed", True)
        and (
            (
                (departments is None or (raw.get("department") or "").strip() in departments)
                and (job_filter is None or job_filter(raw))
            )
            or is_core_title(raw["title"])
        )
        and _is_canada(raw)
    ]
    logger.info("%s: fetched %d matching jobs (of %d total)", name, len(matched), len(raw_jobs))
    return [_normalize(raw) for raw in matched]


def _country(entry: dict) -> str:
    return (((entry.get("address") or {}).get("postalAddress") or {}).get("addressCountry") or "").strip().lower()


def _is_canada(raw: dict) -> bool:
    entries = [raw, *(raw.get("secondaryLocations") or [])]
    return any(
        _country(entry) == "canada" or "canada" in (entry.get("location") or "").lower()
        for entry in entries
    )


def _normalize(raw: dict) -> NormalizedJob:
    locations = [raw.get("location") or ""]
    locations += [s.get("location") or "" for s in raw.get("secondaryLocations") or []]
    location = "; ".join(dict.fromkeys(l.strip() for l in locations if l.strip()))
    category = " / ".join(dict.fromkeys(
        part.strip() for part in (raw.get("department"), raw.get("team")) if part and part.strip()
    ))
    published = raw.get("publishedAt")
    return {
        "external_id": raw["id"],
        "title": raw["title"].strip(),
        "url": raw.get("jobUrl") or "",
        "location": location,
        "category": category,
        "posted_date": published[:10] if published else None,
        "platform": "Ashby",
        "description": clean_description(raw.get("descriptionHtml") or raw.get("descriptionPlain")),
    }
