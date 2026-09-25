"""Ericsson careers scraper, scoped to Canada + Product Development / Technology & Research.

`jobs.ericsson.com` is **Eightfold** (with SuccessFactors behind it), same
`pcsx` search API as Microsoft/Autodesk, via the shared helper in
scrapers/eightfold.py. `location=Canada` returned 28 jobs on 2026-09-25
(Ottawa, Toronto, Mississauga, Montréal).

`department` values carry numeric prefixes; the R&D ones are
"76 Product Development" and "75 Technology & Research".
"""

from .base import NormalizedJob
from .eightfold import scrape_eightfold

DEPARTMENTS = {"76 Product Development", "75 Technology & Research"}


def scrape() -> list[NormalizedJob]:
    return scrape_eightfold(
        name="Ericsson",
        base_url="https://jobs.ericsson.com",
        domain="ericsson.com",
        job_filter=lambda raw: (raw.get("department") or "") in DEPARTMENTS,
    )
