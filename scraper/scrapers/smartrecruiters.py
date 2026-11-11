"""Shared helper for SmartRecruiters public posting API scrapers.

Same API as Ubisoft (see scrapers/ubisoft.py for how it was found):
`GET https://api.smartrecruiters.com/v1/companies/<company>/postings` is
public and unauthenticated.

- `country=<iso2>` is a real server-side filter. Pagination: `limit`
  (max 100) / `offset`, until `totalFound`.
- There's no server-side category filter, and the built-in `function` /
  `department` fields are tenant-specific (Ubisoft's "Information
  Technology" function includes animators), so each company picks its scope
  from a custom field (`customField[]`, by `fieldLabel`), which also
  becomes the job's category. Postings with a core title (data, ML, software) are kept
  whatever the field says.
- Per posting: `id` (stable numeric, external_id), `name`, `releasedDate`
  (ISO), `location.fullLocation`. Job page: `jobs.smartrecruiters.com/<company>/<id>`.
"""

import logging

import httpx

from .base import NormalizedJob, is_core_title

logger = logging.getLogger(__name__)

PAGE_SIZE = 100
MAX_PAGES = 20


def scrape_smartrecruiters(
    *,
    name: str,
    company: str,
    field_label: str,
    field_values: set[str],
    country: str = "ca",
) -> list[NormalizedJob]:
    """Keeps postings whose custom field `field_label` is in `field_values`,
    or whose title is a core title (data, ML, software)."""
    list_url = f"https://api.smartrecruiters.com/v1/companies/{company}/postings"
    jobs: list[NormalizedJob] = []
    offset = 0
    total = 0

    with httpx.Client(timeout=30) as client:
        for _ in range(MAX_PAGES):
            response = client.get(list_url, params={"country": country, "limit": PAGE_SIZE, "offset": offset})
            response.raise_for_status()
            payload = response.json()
            total = payload["totalFound"]
            for raw in payload["content"]:
                value = custom_field(raw, field_label)
                if value in field_values or is_core_title(raw["name"]):
                    jobs.append(_normalize(raw, company, value or ""))
            offset += PAGE_SIZE
            if offset >= total or not payload["content"]:
                break
        else:
            logger.warning("%s scrape hit MAX_PAGES=%d without finishing — got %d jobs", name, MAX_PAGES, len(jobs))

    logger.info("%s: fetched %d matching jobs (of %d %s postings)", name, len(jobs), total, country.upper())
    return jobs


def custom_field(raw: dict, field_label: str) -> str | None:
    return next(
        (field.get("valueLabel") for field in raw.get("customField") or [] if field.get("fieldLabel") == field_label),
        None,
    )


def _normalize(raw: dict, company: str, category: str) -> NormalizedJob:
    released = raw.get("releasedDate")
    return {
        "external_id": str(raw["id"]),
        "title": raw["name"].strip(),
        "url": f"https://jobs.smartrecruiters.com/{company}/{raw['id']}",
        "location": (raw.get("location") or {}).get("fullLocation", ""),
        "category": category,
        "posted_date": released[:10] if released else None,
        "platform": "SmartRecruiters",
    }
