"""StackAdapt careers scraper (Canada / Engineering, Data and IT departments).

Greenhouse board `stackadapt` (stackadapt.com/careers links straight to it),
via the shared helper in scrapers/greenhouse.py.

- 70 postings worldwide, 44 in Canada (2026-10-02); most Canadian postings
  list "Canada; United States" and are kept.
- StackAdapt's department tree is shallow and mixes disciplines under one
  "Advertising Technologies" parent, so the engineering sub-teams are listed
  by name rather than matched through a parent: Back-end / Front-end /
  Platform / Quality Engineering, Dev Ops & Infrastructure, Data Science,
  Business Intelligence, Inventory Development and IT Business Applications.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {
    "Back-end Engineering",
    "Front-end Engineering",
    "Platform Engineering",
    "Quality Engineering",
    "Dev Ops & Infrastructure",
    "Data Science",
    "Business Intelligence",
    "Inventory Development",
    "IT Business Applications",
}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="StackAdapt", board_token="stackadapt", departments=DEPARTMENTS)
