"""Symcor careers scraper, scoped to Canada + technology departments.

symcor.com's careers page links to Dayforce, namespace `symcor`
(`jobs.dayforcehcm.com/en-US/symcor/CANDIDATEPORTAL`), via the shared
helper in scrapers/dayforce.py (see its docstring for the API and CSRF
details).

- On 2026-11-10 there were 4 postings, all in Mississauga, ON, across 4
  departments: "Architecture", "Development - Data", "Product" (product
  management) and "Stationery Support Group" (warehouse).
- Tech scope is departments whose name looks technical (see
  DEPARTMENT_PATTERN), matched at runtime so new ones like "Development -
  Java" or "Infrastructure" get picked up. Product and operations roles
  are left out. The helper's extra search keeps data titles from any
  department.
"""

import re

from .base import NormalizedJob
from .dayforce import scrape_dayforce

DEPARTMENT_PATTERN = re.compile(
    r"architect|develop|engineer|software|technolog|\bIT\b|infrastructure|security|cloud|data|\bQA\b|quality",
    re.IGNORECASE,
)


def scrape() -> list[NormalizedJob]:
    return scrape_dayforce(
        name="Symcor",
        namespace="symcor",
        department_filter=lambda name: bool(DEPARTMENT_PATTERN.search(name)),
    )
