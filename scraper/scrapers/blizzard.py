"""Blizzard careers scraper (Engineering & Technology category, Canada only).

Same Phenom People platform as RBC/BMO (scrapers/rbc.py, scrapers/bmo.py) —
job data is embedded server-side in a `phApp.ddo = {...}` JSON blob, so a
plain HTTP GET is enough, no browser needed. See rbc.py's docstring for the
general shape of this approach.

Blizzard-specific notes (see CLAUDE.md's "Liberty Mutual, Blizzard, Riot
Games, Nvidia, UBC, Reddit, ATS Corporation scraping approach" section):

- Deviation from CLAUDE.md: the job list does NOT live at
  `ddo["eagerLoadRefineSearch"]` like RBC/BMO. For this site it's at
  `ddo["targetedJobs"]` instead (`targetedJobs.totalHits` /
  `targetedJobs.data.jobs`) — confirmed live 2026-09-21. Everything else
  about the blob (per-job fields) matches RBC's shape.
- Category refinement is the query param `rk=l-engineering-technology` on
  the `engineering-technology` category page (not an opaque ID like
  Workday's facets, and not a plain `category=` label like BMO's).
- Pagination: `from=<offset>`, but the confirmed page size here is 5 (not
  RBC/BMO's 10) — first page returned `hits: 5` of `totalHits: 9`. No `s=1`
  param is sent (not documented as needed here, unlike RBC).
- **No confirmed server-side country filter** — every job's real ATS is
  Microsoft's Xbox Gaming Workday tenant (`applyUrl` points at
  `xboxgaming.wd1.myworkdayjobs.com/Blizzard_External_Careers/...`), so
  `platform` is `"Workday"` per CLAUDE.md's stated convention (record the
  real apply backend), not "Phenom". Canada filtering is done client-side
  on each job's own `country` field. CLAUDE.md notes Blizzard currently has
  **zero** Canada postings company-wide — an empty result here is expected,
  not a bug.
"""

from .base import NormalizedJob
from .phenom import scrape_phenom


def scrape() -> list[NormalizedJob]:
    return scrape_phenom(
        name="Blizzard",
        list_url="https://careers.blizzard.com/global/en/engineering-technology",
        params={"rk": "l-engineering-technology"},
        blob_key="targetedJobs",
        platform="Workday",
        job_filter=lambda raw: raw.get("country") == "Canada",
    )
