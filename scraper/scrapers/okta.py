"""Okta careers scraper, scoped to Canada + R&D engineering.

Greenhouse (board token `okta`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 334 jobs, 70 in Canada
(mostly Toronto; some list Toronto alongside US cities).

Department names carry cost-centre suffixes ("SW Eng - Applications-674").
Everything under "R&D" is kept except product management and design. The
product security team sits under "Subscription COGS", so it's listed on
its own.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {"R&D", "Sec - Product Security-771"}
EXCLUDE = {"Product Management-810", "Product Design & UXR-650", "Spera PM-811"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Okta", board_token="okta", departments=DEPARTMENTS, exclude_departments=EXCLUDE)
