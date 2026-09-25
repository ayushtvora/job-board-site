"""Datadog careers scraper, scoped to Canada + Engineering.

Greenhouse (board token `datadog`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 449 jobs, and no Canadian
office in the board's office list. The only Canada-pattern hits were 3
Boston / New York "Dev Eng" postings that `location.name` rules out, so the
Canada check here is on `location.name` only. Expect an empty result until
Datadog posts a Canadian role.
"""

from .base import NormalizedJob
from .greenhouse import location_name_is_canada, scrape_greenhouse


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(
        name="Datadog", board_token="datadog", departments={"Engineering"}, is_canada=location_name_is_canada
    )
