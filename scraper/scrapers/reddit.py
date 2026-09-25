"""Reddit careers scraper (Canada / Engineering department jobs).

job-boards.greenhouse.io/reddit is Greenhouse's own hosted board — the
public Board API is used directly, a single unauthenticated GET returns
every current job in one response, no pagination needed. See CLAUDE.md's
"Liberty Mutual, Blizzard, Riot Games, Nvidia, UBC, Reddit, ATS Corporation
scraping approach" section (Reddit bullet) for how this was found.

- Greenhouse's public Board API has no server-side location filter
  (`location=` query params are silently ignored, confirmed by diffing
  filtered vs. unfiltered responses) — Canada is filtered client-side on
  `location.name`.
- Category scoping uses Greenhouse's real department tree
  (`GET .../departments`) rather than string-matching: the top-level
  "Engineering" department (id 16253) plus its child departments (Ads
  Engineering, Machine Learning, BE Platform, Site Reliability, FE
  Platform, etc., listed in its `child_ids`). Each job's own top-level
  `departments[]` array is checked against that id set. The `metadata[]`
  entry literally named "Department" is NOT used — CLAUDE.md notes it's
  unreliable/null on real jobs.
"""

from .base import NormalizedJob
from .greenhouse import location_name_is_canada, scrape_greenhouse


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(
        name="Reddit",
        board_token="reddit",
        departments={"Engineering"},
        is_canada=location_name_is_canada,
    )
