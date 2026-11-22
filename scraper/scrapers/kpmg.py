"""KPMG Canada careers scraper (tech and data roles).

careers.kpmg.ca is an iCIMS Jibe front-end, via scrapers/jibe.py.
Investigated 2026-11-22. KPMG US is a separate member firm with its own
site and module (kpmgus.py).

- `/api/jobs?limit=100` works: 446 postings in 5 pages, all Canadian.
  robots.txt asks for `crawl-delay: 5`, so pages are fetched 5s apart.
- Scope is the "Information Technology" and "Digital" categories, core
  titles, and hands-on cyber / cloud / AI titles, which sit under Advisory.
  SR&ED tax consultants ("Senior SR&ED Consultant (Software Engineering)")
  are left out, as at EY.
- `full_location` has no province ("Abbotsford, Canada"), which job_cities
  needs for smaller cities, so the location is built from the city and
  state of the primary and `additional_locations`.
"""

import re

from .base import NormalizedJob, is_core_title
from .jibe import categories, scrape_jibe

CATEGORIES = {"Information Technology", "Digital"}
TECH_TITLE_PATTERN = re.compile(
    r"cyber *(?:security|defen[cs]e)|offensive security|cloud security|SOC analyst|"
    r"(?-i:\bAI\b) (?:architect|& copilot)|copilot and (?-i:AI)\b|\btech(?:nical)? lead",
    re.IGNORECASE,
)
EXCLUDED_TITLE_PATTERN = re.compile(r"SR&ED")


def _matches(raw: dict) -> bool:
    title = raw.get("title") or ""
    if raw.get("country_code") != "CA" or EXCLUDED_TITLE_PATTERN.search(title):
        return False
    return (
        any(c in CATEGORIES for c in categories(raw))
        or is_core_title(title)
        or bool(TECH_TITLE_PATTERN.search(title))
    )


def _location(raw: dict) -> str:
    places = [raw, *(raw.get("additional_locations") or [])]
    names = [", ".join(p[key] for key in ("city", "state", "country") if p.get(key)) for p in places]
    return "; ".join(dict.fromkeys(name for name in names if name))


def scrape() -> list[NormalizedJob]:
    return scrape_jibe(
        name="KPMG",
        base_url="https://careers.kpmg.ca",
        job_path="/jobs",
        params={"limit": "100"},
        page_delay=5,
        job_filter=_matches,
        location_fn=_location,
    )
