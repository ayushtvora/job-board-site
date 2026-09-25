"""Ubisoft careers scraper, scoped to Canada + software/IT/data job families.

Ubisoft's careers search (ubisoft.com/.../careers/search) is an Algolia
index over **SmartRecruiters** data; SmartRecruiters' public posting API is
open and simpler: `GET https://api.smartrecruiters.com/v1/companies/Ubisoft2/postings`
(company identifier `Ubisoft2`; `Ubisoft` returns an empty company). Via
the shared helper in scrapers/smartrecruiters.py.

- `country=ca` is a real server-side filter (159 of 309 postings,
  2026-09-25 — Montréal, Québec City, Toronto, Halifax, Sherbrooke, ...).
- Category: SmartRecruiters' `function` field is too coarse here
  ("Information Technology" includes animators and riggers), so the scope
  is the "Job Family" custom field: "Software Development", "Information &
  Systems", "Data".
- Many Québec roles are posted twice, as separate English and French
  postings with distinct IDs. Both are kept, since the source site lists
  them as separate postings.
"""

from .base import NormalizedJob
from .smartrecruiters import scrape_smartrecruiters

JOB_FAMILIES = {"Software Development", "Information & Systems", "Data"}


def scrape() -> list[NormalizedJob]:
    return scrape_smartrecruiters(name="Ubisoft", company="Ubisoft2", field_label="Job Family", field_values=JOB_FAMILIES)
