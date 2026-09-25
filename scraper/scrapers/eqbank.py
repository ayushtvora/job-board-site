"""EQ Bank (Equitable Bank) careers scraper, scoped to technology departments.

Lever postings API (company `eqbank`), via the shared helper in
scrapers/lever.py. Equitable's Dayforce portal is only its internal HR
system; external applications go through jobs.lever.co/eqbank.
Investigated 2026-09-25: 87 postings, all `country == "CA"`.

There's no single tech department. Tech is spread across "IT Platform",
"Infrastructure & Operations", "AI COE", "Enterprise Functions Technology",
"Commercial Lending Technology", "Retail Lending Technology", "Technology
Workspace", "Information Security", "CB - Cyber & IT Security", and the data
teams, so departments are matched by keyword.
"""

import re

from .base import NormalizedJob
from .lever import scrape_lever

TECH_DEPARTMENT_PATTERN = re.compile(r"technology|\bIT\b|\bAI\b|infrastructure|security|data", re.IGNORECASE)


def scrape() -> list[NormalizedJob]:
    return scrape_lever(
        name="EQ Bank",
        company="eqbank",
        department_filter=lambda department: bool(TECH_DEPARTMENT_PATTERN.search(department)),
    )
