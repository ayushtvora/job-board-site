"""Jane Street careers scraper (Canada / technology departments).

janestreet.com's open-roles page is fed by `/jobs/main.json`, whose job IDs
are Greenhouse IDs; the Greenhouse board `janestreet` has the same 230
postings with proper departments and locations, so it's used via
scrapers/greenhouse.py.

Jane Street has no Canadian office: every posting on 2026-10-02 was in New
York, London, Hong Kong, Singapore, Austin or Chicago, so an empty result
is expected.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {
    "Software Engineering",
    "IT and Systems Engineering",
    "Machine Learning",
    "Network Engineering",
    "Cybersecurity",
    "Quantitative Research",
}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Jane Street", board_token="janestreet", departments=DEPARTMENTS)
