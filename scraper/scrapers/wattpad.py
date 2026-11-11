"""Wattpad careers scraper (Canada, engineering titles).

Lever, company `wattpad` (company.wattpad.com/jobs loads
`api.lever.co/v0/postings/wattpad`), via scrapers/lever.py. Investigated
2026-11-10: 2 postings, both Toronto engineering leadership. Every
posting's department is just "Wattpad", so scope is by title.
"""

import re

from .base import NormalizedJob, is_core_title
from .lever import scrape_lever

TECH_TITLE_PATTERN = re.compile(r"engineer|technical|architect", re.IGNORECASE)


def scrape() -> list[NormalizedJob]:
    jobs = scrape_lever(name="Wattpad", company="wattpad", department_filter=lambda _department: True)
    return [job for job in jobs if TECH_TITLE_PATTERN.search(job["title"]) or is_core_title(job["title"])]
