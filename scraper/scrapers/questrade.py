"""Questrade (Questrade Financial Group) careers scraper, scoped to Canada + technology departments.

Questrade's careers page links to Dayforce, namespace `qfg`
(`jobs.dayforcehcm.com/en-US/qfg/CANDIDATEPORTAL`), via the shared helper
in scrapers/dayforce.py (see its docstring for the API + CSRF details).

- Departments are "<Group> : <Team>" strings; technology is everything
  under "Technology : ..." (engineering teams) and "TSS : ..." (Technology
  Shared Services — platform, infra/cloud, AI engineering, cybersecurity).
  Matched by prefix at runtime so new teams are picked up automatically.
  20 jobs across 12 such departments on 2026-09-25.
- Questrade also posts roles in Argentina and Israel on the same board, so
  postings are filtered to `isoCountryCode == "CA"`.
"""

from .base import NormalizedJob
from .dayforce import scrape_dayforce

DEPARTMENT_PREFIXES = ("Technology :", "TSS :")


def scrape() -> list[NormalizedJob]:
    return scrape_dayforce(
        name="Questrade",
        namespace="qfg",
        department_filter=lambda name: name.startswith(DEPARTMENT_PREFIXES),
    )
