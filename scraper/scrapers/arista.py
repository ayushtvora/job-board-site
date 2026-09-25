"""Arista Networks careers scraper, scoped to Canada + Software / Hardware Engineering.

arista.com/en/careers is backed by **SmartRecruiters** (company
`AristaNetworks`), via the shared helper in scrapers/smartrecruiters.py.
`country=ca` gave 25 postings on 2026-09-25, almost all Vancouver EOS
software engineering.

The `function` field is inconsistent (software roles appear under both
"Engineering" and "Information Technology"), so scope comes from the
"Department" custom field: "Software Engineering", plus "Hardware
Engineering" for when it shows up in Canada.
"""

from .base import NormalizedJob
from .smartrecruiters import scrape_smartrecruiters

DEPARTMENTS = {"Software Engineering", "Hardware Engineering"}


def scrape() -> list[NormalizedJob]:
    return scrape_smartrecruiters(
        name="Arista", company="AristaNetworks", field_label="Department", field_values=DEPARTMENTS
    )
