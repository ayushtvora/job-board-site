"""Instacart careers scraper, scoped to Canada + Engineering.

Greenhouse (board token `instacart`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 109 jobs total; Canadian
roles are remote, `location.name` = "Canada - Remote (ON, AB, BC, or NS
Only)", or carry a "Remote - Canada" office alongside "Remote - United
States" (open to either country — kept).

Departments: the "Engineering" parent (children: Software Engineering,
Machine Learning, Infrastructure, Mobile, Security, IT, Leadership
(Engineering)), minus "Professional Services" — technical account
management, not engineering, despite sitting under it.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {"Engineering"}
EXCLUDE_DEPARTMENTS = {"Professional Services"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(
        name="Instacart",
        board_token="instacart",
        departments=DEPARTMENTS,
        exclude_departments=EXCLUDE_DEPARTMENTS,
    )
