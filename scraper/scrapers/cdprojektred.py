"""CD PROJEKT RED careers scraper (Canada / technical departments).

SmartRecruiters company `cdprojektred`, via scrapers/smartrecruiters.py.
The studio in Vancouver (formerly Digital Scapes) and a Montreal team post
here alongside Warsaw and Boston.

- 43 postings worldwide on 2026-10-02, 5 in Canada (an IT Technician in
  Vancouver plus production/research roles).
- Scope is the "Department" custom field: Engineering, Technical Support,
  QA and Studio Operations (which holds the IT systems roles).
"""

from .base import NormalizedJob
from .smartrecruiters import scrape_smartrecruiters


def scrape() -> list[NormalizedJob]:
    return scrape_smartrecruiters(
        name="CD PROJEKT RED",
        company="cdprojektred",
        field_label="Department",
        field_values={"Engineering", "Technical Support", "QA", "Studio Operations"},
    )
