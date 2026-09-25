"""Ubisoft careers scraper, scoped to Canada + software/IT/data job families.

Ubisoft's careers search (ubisoft.com/.../careers/search) is an Algolia
index over **SmartRecruiters** data; SmartRecruiters' public posting API is
open and simpler: `GET https://api.smartrecruiters.com/v1/companies/Ubisoft2/postings`
(company identifier `Ubisoft2` — `Ubisoft` returns an empty company).

- `country=ca` is a real server-side filter (159 of 309 postings,
  2026-09-25 — Montréal, Québec City, Toronto, Halifax, Sherbrooke, ...).
  Pagination: `limit` (max 100) / `offset`, until `totalFound`.
- Category: SmartRecruiters' `function` field is too coarse here
  ("Information Technology" includes animators and riggers), so the scope
  is the "Job Family" custom field: "Software Development", "Information &
  Systems", "Data".
- Many Québec roles are posted twice, as separate English and French
  postings with distinct IDs — both are kept, since they're distinct
  postings on the source site.
- Fields: `id` (stable numeric, external_id), `name`, `releasedDate` (ISO),
  `location.fullLocation`. Job page: `jobs.smartrecruiters.com/Ubisoft2/<id>`.
"""

import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

LIST_URL = "https://api.smartrecruiters.com/v1/companies/Ubisoft2/postings"
JOB_URL_TEMPLATE = "https://jobs.smartrecruiters.com/Ubisoft2/{id}"
JOB_FAMILIES = {"Software Development", "Information & Systems", "Data"}
PAGE_SIZE = 100
MAX_PAGES = 20


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    offset = 0
    total = 0

    with httpx.Client(timeout=30) as client:
        for _ in range(MAX_PAGES):
            response = client.get(LIST_URL, params={"country": "ca", "limit": PAGE_SIZE, "offset": offset})
            response.raise_for_status()
            payload = response.json()
            total = payload["totalFound"]
            for raw in payload["content"]:
                if _job_family(raw) in JOB_FAMILIES:
                    jobs.append(_normalize(raw))
            offset += PAGE_SIZE
            if offset >= total or not payload["content"]:
                break
        else:
            logger.warning("Ubisoft scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info("Ubisoft: fetched %d matching jobs (of %d Canada postings)", len(jobs), total)
    return jobs


def _job_family(raw: dict) -> str | None:
    return next(
        (field.get("valueLabel") for field in raw.get("customField") or [] if field.get("fieldLabel") == "Job Family"),
        None,
    )


def _normalize(raw: dict) -> NormalizedJob:
    released = raw.get("releasedDate")
    return {
        "external_id": str(raw["id"]),
        "title": raw["name"].strip(),
        "url": JOB_URL_TEMPLATE.format(id=raw["id"]),
        "location": (raw.get("location") or {}).get("fullLocation", ""),
        "category": _job_family(raw) or "",
        "posted_date": released[:10] if released else None,
        "platform": "SmartRecruiters",
    }
