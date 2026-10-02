"""Hudson River Trading careers scraper (Canada / technology departments).

hudsonrivertrading.com/careers renders jobs from Greenhouse board
`wehrtyou` (the site's job links are `/careers/job/?gh_jid=<id>`;
`hrttalentcommunity` is only the talent-community form). Via
scrapers/greenhouse.py.

HRT has no Canadian office: all 87 postings on 2026-10-02 were in the US,
London or Singapore, so an empty result is expected. Scope is the
engineering/research departments in case that changes.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {
    "Algo",
    "Data",
    "PostTrade",
    "Productivity",
    "Research & Development Platform",
    "Trading Tech",
    "Acceleration",
}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Hudson River Trading", board_token="wehrtyou", departments=DEPARTMENTS)
