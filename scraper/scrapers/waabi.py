"""Waabi careers scraper, scoped to Canada + Software / Hardware / co-ops.

Lever postings API (company `waabi`), via the shared helper in
scrapers/lever.py. Investigated 2026-09-25: 88 postings, 26 with
`country == "CA"` (Toronto). The CA-coded postings are in the "Software"
(Autonomy & Algorithms, Software Engineering, Corporate IT), "Hardware" and
"Internships / Co-ops" departments, plus a few non-tech ones.
"""

from .base import NormalizedJob
from .lever import scrape_lever

DEPARTMENTS = {"Software", "Hardware", "Internships / Co-ops"}


def scrape() -> list[NormalizedJob]:
    return scrape_lever(name="Waabi", company="waabi", department_filter=lambda department: department in DEPARTMENTS)
