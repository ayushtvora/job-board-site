"""Spotify careers scraper, scoped to Canada + Engineering.

lifeatspotify.com's own API only does client-side filtering and is a thin
wrapper; the real backend ATS is Lever, confirmed via each job's `apply`
link pointing at `jobs.lever.co/spotify/...`. See CLAUDE.md's "Intel,
Oracle, Spotify, Adobe, Sony, AMD, Uber scraping approach" section (Spotify
bullet) for how this was found.

- `GET https://api.lever.co/v0/postings/spotify?mode=json` returns the full
  current posting list in one call (~71 postings at investigation time) —
  no pagination needed at this size, though `skip=` exists on Lever's API
  if that ever changes.
- No server-side Canada/category filter — each posting carries `country`
  (ISO-2, e.g. "CA") and `categories.department`, filtered client-side here.
- CLAUDE.md documents 0 real Canada + Engineering matches at investigation
  time (the one Canada posting found was department "Data and Analytics",
  not Engineering) — a legitimate empty result, not a bug.
"""

from .base import NormalizedJob
from .lever import scrape_lever


def scrape() -> list[NormalizedJob]:
    return scrape_lever(
        name="Spotify",
        company="spotify",
        department_filter=lambda department: "engineering" in department.lower(),
    )
