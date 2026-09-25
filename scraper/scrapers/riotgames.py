"""Riot Games careers scraper (Canada / Engineering jobs).

riotgames.com/en/work-with-us is a custom React site, but each job's detail
page embeds the standard Greenhouse widget (board token "riotgames"), so the
canonical data source is Greenhouse's public Board API — a single
unauthenticated GET returns every current job in one response, no pagination
needed. See CLAUDE.md's "Liberty Mutual, Blizzard, Riot Games, Nvidia, UBC,
Reddit, ATS Corporation scraping approach" section (Riot Games bullet) for
how this was found.

- Greenhouse's public Board API has no server-side location filter
  (`location=` query params are silently ignored) — Canada is filtered
  client-side on `location.name`.
- There's also no single category/department facet that maps cleanly to
  "Engineering" here; instead each job's `metadata[]` array has a `"Craft"`
  field. Confirmed values include "Software Engineering Group", "Engineering",
  "Infrastructure", "QA Group", "Data", among many non-technical ones (e.g.
  "Art", "Esports", "Finance"). This scraper treats "Software Engineering
  Group", "Engineering", and "Infrastructure" as the software-engineering-ish
  subset — "QA Group" and "Data" are adjacent but not core software
  engineering, so they're excluded.
- As of the CLAUDE.md investigation there were 0 Canada postings company-wide
  (confirmed against the site's own location dropdown) — an empty result
  here is expected, not a scraper bug.
"""

from .base import NormalizedJob
from .greenhouse import location_name_is_canada, metadata_value, scrape_greenhouse

# Craft values (from each job's metadata[]) treated as software-engineering-ish.
ENGINEERING_CRAFTS = {"Software Engineering Group", "Engineering", "Infrastructure"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(
        name="Riot Games",
        board_token="riotgames",
        departments=None,
        job_filter=lambda raw: metadata_value(raw, "Craft") in ENGINEERING_CRAFTS,
        is_canada=location_name_is_canada,
        category_fn=lambda raw: metadata_value(raw, "Craft") or "",
    )
