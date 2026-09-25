"""Intuit careers scraper, scoped to Canada + Software Engineering.

`jobs.intuit.com` is a Radancy TalentBrew career site (org ID `27595`), via
the shared helper in scrapers/talentbrew.py. Applications go to Avature
(`intuit.avature.net`), so `platform` = "Avature".

- Category facet "Software Engineering" = `68357` (11 of 25 Canadian jobs,
  2026-09-25, all Toronto; includes co-op roles).
- The result list has no posted date (only the detail page's JSON-LD does),
  so `posted_date` is None and the UI falls back to first-seen.
"""

from .base import NormalizedJob
from .talentbrew import scrape_talentbrew


def scrape() -> list[NormalizedJob]:
    return scrape_talentbrew(
        name="Intuit",
        base_url="https://jobs.intuit.com",
        org_id="27595",
        category_ids=["68357"],
        category_label="Software Engineering",
        platform="Avature",
    )
