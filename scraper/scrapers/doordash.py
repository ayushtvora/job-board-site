"""DoorDash careers scraper, scoped to Canada + Engineering / Data.

Greenhouse, via the shared helper in scrapers/greenhouse.py. DoorDash runs
separate boards per region: `doordashusa` (456 jobs, whose only "Canada"
hits are Vancouver, *WA*), `doordashinternational` (none in Canada), and
**`doordashcanada`**, used here (35 jobs on 2026-09-25, all Toronto,
Vancouver or remote Canada). careers.doordash.com is 403'd.

Departments carry numeric prefixes ("310 Engineering" > "347 Ads
Engineering"); the parents "310 Engineering" and "330 Data" are matched.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {"310 Engineering", "330 Data"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="DoorDash", board_token="doordashcanada", departments=DEPARTMENTS)
