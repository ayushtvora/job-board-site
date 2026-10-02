"""Anthropic careers scraper (Canada / engineering and research departments).

Also covers "Claude", which is Anthropic's product rather than a separate
employer. Greenhouse board `anthropic`, via scrapers/greenhouse.py.

- 637 postings worldwide, 8 mentioning Canada (2026-10-02), mostly
  "Ontario, CAN"; CANADA_PATTERN matches the province name.
- Scope is the technical top-level departments. "Compute" is left out
  because its Canadian postings are deal and community roles, and
  "Applied AI" because it's mostly customer-facing.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {
    "AI Research & Engineering",
    "Software Engineering - Infrastructure",
    "Engineering & Design - Product",
    "Security",
    "Data Science & Analytics",
    "Safeguards (Trust & Safety)",
}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Anthropic", board_token="anthropic", departments=DEPARTMENTS)
