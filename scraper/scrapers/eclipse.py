"""Eclipse Automation careers scraper, scoped to Canada + software/engineering roles.

Unblocked 2026-09-25, once Dayforce's platform-wide maintenance ended.
Namespace `eclipse` (`jobs.dayforcehcm.com/en-CA/eclipse/CANDIDATEPORTAL`),
via the shared helper in scrapers/dayforce.py (see its docstring for the
API and CSRF details).

- There were 48 postings, all in Canada (Cambridge, ON), on 2026-09-25.
- **Department tagging is sparse**: only 3 departments exist
  ("Applications", "Electrical Engineering", "Sales"). Most postings,
  including "AI Software Engineer" and "Nvidia Omniverse Developer", have
  no department, so a department filter would miss them.
- Instead, every job is fetched and kept if its title looks like software,
  IT, data, AI or engineering work (see TITLE_PATTERN).
- Shop-floor trades (millwright, machinist, CNC programmer, electrician,
  panel builder) and business roles are left out.
"""

import re

from .base import NormalizedJob
from .dayforce import scrape_dayforce

TITLE_PATTERN = re.compile(r"software|developer|engineer|\bIT\b|\bAI\b|data|scada|controls", re.IGNORECASE)


def scrape() -> list[NormalizedJob]:
    jobs = scrape_dayforce(name="Eclipse Automation", namespace="eclipse")
    return [
        {**job, "category": job["category"] or "Engineering"}
        for job in jobs
        if TITLE_PATTERN.search(job["title"])
    ]
