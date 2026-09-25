"""D2L careers scraper, scoped to Canada + Product Development.

D2L's careers page (`d2l.com/careers/jobs/`) is a WordPress listing whose
job links carry `gh_jid=` — the backend is Greenhouse, board token `d2l`,
via the shared helper in scrapers/greenhouse.py. (D2L also still has a
Lever board, `jobs.lever.co/d2l`, but its postings date from 2019 — stale,
not the live source.)

Investigated 2026-09-25: 19 jobs total, 16 Canadian (mostly Kitchener /
Toronto / "Canada Remote"). Department "Product Development" is D2L's
engineering org (software developers, security analysts, new-grad roles).
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {"Product Development"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="D2L", board_token="d2l", departments=DEPARTMENTS)
