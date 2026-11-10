"""Xanadu careers scraper, scoped to Canada + software / computing roles.

xanadu.ai/careers links to **HiBob**'s hosted careers site
(`xanadu.careers.hibob.com`), found in the careers page's JS bundle. Its
Angular front-end loads every job ad from one endpoint:
`GET https://xanadu.careers.hibob.com/api/job-ad`. The endpoint needs a
`companyidentifier: xanadu` header (401 without it) but no session or
token. Investigated 2026-09-25: 73 ads, 70 in Canada (Toronto, plus remote
and Québec).

- Per ad: `id` (UUID, external_id), `title`, `department` (only
  "Hardware", "Operations", "Software"), `site`, `country`, `publishedAt`
  (ISO datetime). Job page: `https://xanadu.careers.hibob.com/jobs/<id>`.
- The three departments are coarse, and software roles also appear under
  Hardware / Operations ("Quantum Architecture Research Software
  Developer", "Cloud Engineer"). So jobs are kept if the department is
  "Software", or if the title looks like a software/data/computing role.
"""

import logging
import re

import httpx

from .base import NormalizedJob, clean_description, is_data_title

logger = logging.getLogger(__name__)

API_URL = "https://xanadu.careers.hibob.com/api/job-ad"
JOB_URL_TEMPLATE = "https://xanadu.careers.hibob.com/jobs/{id}"
TECH_TITLE_PATTERN = re.compile(
    r"software|developer|data|cloud|\bAI\b|machine learning|cyber|security|devops|\bIT\b|platform", re.IGNORECASE
)


def scrape() -> list[NormalizedJob]:
    response = httpx.get(API_URL, headers={"companyidentifier": "xanadu"}, timeout=30)
    response.raise_for_status()
    ads = response.json()["jobAdDetails"]
    jobs = [
        _normalize(ad)
        for ad in ads
        if ad.get("country") == "Canada"
        and (
            ad.get("department") == "Software"
            or TECH_TITLE_PATTERN.search(ad.get("title") or "")
            or is_data_title(ad.get("title") or "")
        )
    ]
    logger.info("Xanadu: fetched %d matching jobs (of %d total)", len(jobs), len(ads))
    return jobs


def _normalize(ad: dict) -> NormalizedJob:
    published = ad.get("publishedAt")
    location = ", ".join(part for part in (ad.get("site"), ad.get("country")) if part)
    return {
        "external_id": ad["id"],
        "title": ad["title"].strip(),
        "url": JOB_URL_TEMPLATE.format(id=ad["id"]),
        "location": location,
        "category": ad.get("department") or "",
        "posted_date": published[:10] if published else None,
        "platform": "HiBob",
        # The list response has the whole posting, in three HTML fields.
        "description": clean_description(
            "".join(ad.get(key) or "" for key in ("description", "responsibilities", "requirements"))
        ),
    }
