"""Airbnb careers scraper (Canada / Software Engineering department jobs).

careers.airbnb.com is a custom front-end, but its job-detail "Apply Now"
embed points at Greenhouse (board token "airbnb") — the public Board API is
used directly, a single unauthenticated GET returns every current job in one
response, no pagination needed. See CLAUDE.md's "Airbnb, Databricks, Stripe
scraping approach" section (Airbnb bullet) for how this was found.

- Greenhouse's public Board API has no server-side location filter
  (`location=` query params are silently ignored) — Canada is filtered
  client-side on `location.name`.
- Category scoping uses Greenhouse's real department id for "Software
  Engineering" (77), confirmed against the board's own `/departments`
  endpoint, via each job's top-level `departments[]` array.
- As of the CLAUDE.md investigation, 0 jobs matched Canada + Software
  Engineering simultaneously (Canada jobs exist at Airbnb, just not in this
  department right now) — an empty result here is expected, not a scraper
  bug.
"""

from .base import NormalizedJob
from .greenhouse import location_name_is_canada, scrape_greenhouse


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(
        name="Airbnb",
        board_token="airbnb",
        departments={"Software Engineering"},  # department id 77
        is_canada=location_name_is_canada,
    )
