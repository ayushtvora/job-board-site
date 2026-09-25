"""Qualcomm careers scraper, scoped to Canada + engineering departments.

`careers.qualcomm.com` is **Eightfold**, same `pcsx` search API as
Microsoft/Autodesk, via the shared helper in scrapers/eightfold.py.
`location=Canada` returned 87 jobs on 2026-09-25 (Markham, Toronto, Ottawa,
Vancouver). A couple were San Diego postings that match only loosely, so
the job's own locations are checked too.

`department` holds the engineering discipline ("ASICS Engineering",
"Machine Learning Engineering", "Software Engineering", "Interim
Engineering Intern - SW", "Mask Layout Design", ...); anything with
"Engineering" or "Design" is kept, leaving out program management/analysts.
"""

import re

from .base import CANADA_PATTERN, NormalizedJob
from .eightfold import scrape_eightfold

DEPARTMENT_PATTERN = re.compile(r"engineering|design", re.IGNORECASE)


def scrape() -> list[NormalizedJob]:
    return scrape_eightfold(
        name="Qualcomm",
        base_url="https://careers.qualcomm.com",
        domain="qualcomm.com",
        job_filter=_keep,
    )


def _keep(raw: dict) -> bool:
    locations = raw.get("locations") or []
    return bool(DEPARTMENT_PATTERN.search(raw.get("department") or "")) and any(
        CANADA_PATTERN.search(location) for location in locations
    )
