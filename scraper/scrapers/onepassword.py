"""1Password careers scraper, scoped to Canada + Technology.

Ashby public job-board API (org `1password`), via the shared helper in
scrapers/ashby.py. (Module is `onepassword.py` since a Python module name
can't start with a digit; the company slug is still "1password".)

Investigated 2026-09-25: 63 jobs total. Most are "Remote (United States |
Canada)" — matched as Canada by the helper's location-name check, since
the address country is blank on those — plus a few in Toronto.
Department "Technology" covers Product Engineering, Security, Platform
Engineering, Developer AI, and IT teams.
"""

from .ashby import scrape_ashby
from .base import NormalizedJob

DEPARTMENTS = {"Technology"}


def scrape() -> list[NormalizedJob]:
    return scrape_ashby(name="1Password", org="1password", departments=DEPARTMENTS)
