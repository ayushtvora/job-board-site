"""Metrolinx careers scraper — IT-adjacent roles.

Metrolinx's careers page links out to Oracle Fusion Cloud Recruiting (a
different Oracle Cloud pod/tenant than the Oracle-the-corporation scraper —
these are two independent hosted instances of the same underlying Oracle
product, not a shared backend). Public, unauthenticated REST API — no
browser/session needed. See CLAUDE.md's "Metrolinx scraping approach"
section for how this was found.

- The full `expand=requisitionList.secondaryLocations,flexFieldsFacet.values`
  query param is required on every request — omitting it silently returns
  facet metadata with no `requisitionList` at all (a 200 that looks fine
  but isn't).
- No country filter needed: every currently-open job is already Canada
  (Metrolinx is an Ontario transit agency).
- No dedicated tech/IT category facet exists on this site. Per CLAUDE.md,
  given the small total job count (~38), this scraper pulls *all* jobs and
  keyword-matches titles for "I&IT" / "IT" / "Software" / "Developer" /
  "Systems" (case-insensitive) rather than filtering server-side. `Category`
  is recorded as free text using the matched keyword, since there's no real
  per-job category field to read (`JobFamily`/`JobFunction`/`Department`/
  `Organization` are null on every job, confirmed live).
"""

import re

from .base import NormalizedJob, is_data_title
from .oracle_recruiting import scrape_oracle_recruiting

# CLAUDE.md's recommended keyword list for spotting IT-adjacent titles at a
# site with no real tech/IT category facet. "IT" alone is matched as a
# whole word only, to avoid false positives like "Administrative" or
# "Visit".
_KEYWORD_PATTERN = re.compile(r"I&IT|\bIT\b|Software|Developer|Systems", re.IGNORECASE)


def _category(raw: dict) -> str:
    match = _KEYWORD_PATTERN.search(raw["Title"])
    return match.group(0) if match else "Data"


def scrape() -> list[NormalizedJob]:
    return scrape_oracle_recruiting(
        name="Metrolinx",
        host="ehtc.fa.ca2.oraclecloud.com",
        facets_list="LOCATIONS;WORK_LOCATIONS;TITLES;CATEGORIES;ORGANIZATIONS;POSTING_DATES;FLEX_FIELDS",
        expand="requisitionList.secondaryLocations,flexFieldsFacet.values",
        sort_by="POSTING_DATES_DESC",
        job_filter=lambda raw: bool(_KEYWORD_PATTERN.search(raw.get("Title") or "")) or is_data_title(raw.get("Title") or ""),
        category_fn=_category,
    )
