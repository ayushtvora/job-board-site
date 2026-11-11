"""Visier careers scraper, scoped to Canada + Development.

Ashby, org `visier`, via scrapers/ashby.py (visier.com/company/careers
links to it). Investigated 2026-11-10: 2 postings, both Vancouver.
Engineering departments are named "Development / <team>", so scope is any
department starting with "Development".
"""

from .ashby import scrape_ashby
from .base import NormalizedJob


def scrape() -> list[NormalizedJob]:
    return scrape_ashby(
        name="Visier",
        org="visier",
        departments=None,
        job_filter=lambda raw: (raw.get("department") or "").startswith("Development"),
    )
