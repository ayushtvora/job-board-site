"""Fidelity Investments Canada careers scraper (IT, Analytics, Security).

Workday CXS API, tenant `fil.wd3.myworkdayjobs.com` (Fidelity
International's tenant), site `fidelitycanada`, linked from
careers.fidelity.ca, via scrapers/workday_cxs.py. Investigated 2026-11-10:
153 postings, all Canadian (Toronto, Mississauga, Montreal, Calgary,
Vancouver), so no country facet is needed.

- `jobFamily`: "Canada Information Technology" (43), "Canada Analytics",
  "Canada Security".
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

JOB_FAMILIES = [
    "20a9a0e8b14701932477fd77df4d4e27",  # Canada Information Technology
    "20a9a0e8b14701efcfd5dc77df4d3827",  # Canada Analytics
    "20a9a0e8b14701ce48311e78df4d6627",  # Canada Security
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Fidelity Canada",
        base_url="https://fil.wd3.myworkdayjobs.com",
        tenant="fil",
        site="fidelitycanada",
        applied_facets={"jobFamily": JOB_FAMILIES},
        category_label="Information Technology",
    )
