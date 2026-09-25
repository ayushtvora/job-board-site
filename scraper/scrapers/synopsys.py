"""Synopsys careers scraper, scoped to Canada + Engineering.

`careers.synopsys.com` is a Radancy TalentBrew career site (org ID `44408`),
via the shared helper in scrapers/talentbrew.py. Applications go to Avature
(`synopsys.avature.net`), so `platform` = "Avature".

- Category facet "Engineering" = `8675488` (40 of 43 Canadian jobs,
  2026-09-25: Ottawa, Toronto, Mississauga, Burnaby, "Canada Off-site").
- Results show a real posted date ("Posted: 09/14/2026").
"""

from .base import NormalizedJob
from .talentbrew import scrape_talentbrew


def scrape() -> list[NormalizedJob]:
    return scrape_talentbrew(
        name="Synopsys",
        base_url="https://careers.synopsys.com",
        org_id="44408",
        category_ids=["8675488"],
        category_label="Engineering",
        platform="Avature",
    )
