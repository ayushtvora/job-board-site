"""AMD careers scraper (Canada / Engineering, IT and engineering co-ops).

Unblocked 2026-10-02. The 2026-09-19 investigation hit an AWS WAF captcha
on every request to the iCIMS backend (`careers-amd.icims.com`), but the
public site `careers.amd.com` is an iCIMS "Jibe" front-end whose own JSON
API is open, so this goes through scrapers/jibe.py and never touches
iCIMS directly.

- `location=Canada` is a real server-side filter (129 jobs on 2026-10-02,
  all `country_code` "CA": Markham, Toronto, Calgary, Vancouver).
- Categories in Canada: Engineering (95), "Student / Intern / Temp" (30,
  mostly engineering co-ops), plus a few sales/admin. Scope is
  Engineering and Information Technology, plus co-ops whose title names a
  software, firmware, hardware, data or engineering role.
- Job pages are `/careers-home/jobs/<reqId>?lang=en-us`.
"""

import re

from .base import NormalizedJob
from .jibe import categories, scrape_jibe

CATEGORIES = {"Engineering", "Information Technology"}
STUDENT_CATEGORY = "Student / Intern / Temp"
STUDENT_TITLE_PATTERN = re.compile(r"engineer|software|firmware|hardware|data|developer|libraries|design verification", re.IGNORECASE)


def _matches(raw: dict) -> bool:
    cats = categories(raw)
    if raw.get("country_code") != "CA":
        return False
    if any(c in CATEGORIES for c in cats):
        return True
    return STUDENT_CATEGORY in cats and bool(STUDENT_TITLE_PATTERN.search(raw.get("title") or ""))


def scrape() -> list[NormalizedJob]:
    return scrape_jibe(
        name="AMD",
        base_url="https://careers.amd.com",
        job_path="/careers-home/jobs",
        params={"location": "Canada"},
        job_filter=_matches,
    )
