"""JPMorgan Chase careers scraper (Canada + US, non-senior tech and data roles).

Oracle Recruiting Cloud, pod host `jpmc.fa.oraclecloud.com`, site CX_1001,
via scrapers/oracle_recruiting.py. Investigated 2026-11-22.

- **The one company scoped to the US as well as Canada**, on request (I have
  a referral). Don't copy that to other companies.
- `selectedLocationsFacet` takes both country IDs, semicolon-joined: 5,149
  postings, 17 of them Canadian (none in tech or data on 2026-11-22).
- Scope is JobFunction "Technology" or "Data & Analytics", plus core titles
  in any function, minus senior titles: about 230 of the 1,190 tech and
  data jobs. It's filtered client-side, so one pass over every posting
  covers everything and no keyword searches are needed.
- **Senior titles are skipped**, on request, and only for this company:
  senior (including Senior Associate), lead, principal, staff, architect,
  manager, head of, VP, director. "Engineer II / III", Associate and
  Analyst stay. So do titles open to associates that also name a higher
  level or a manager role ("Vice President/Associate", "Data Product
  Manager - Associate"). "Chief" alone isn't matched, as it's in team
  names ("Chief Data & Analytics Office").
- `limit` is capped at 200, so a run is 26 requests (~50s). Paging was
  stable across three full passes. A short read raises instead of returning,
  because a partial list would delete hundreds of rows along with their
  Will Apply choices.
- The feed still lists a few deleted requisitions (`Id` ends
  `_ORA_DELETED`, with an empty job page), which are dropped.
- Locations: the primary plus `secondaryLocations` in Canada or the US,
  Canadian ones first. Descriptions come from descriptions.py's Oracle
  fetcher.
"""

import re

from .base import NormalizedJob, is_core_title
from .oracle_recruiting import scrape_oracle_recruiting

CANADA_FACET_ID = "300000000289162"
US_FACET_ID = "300000000289738"
COUNTRIES = ("CA", "US")  # also the order locations are shown in
JOB_FUNCTIONS = {"Technology", "Data & Analytics"}
SENIOR_TITLE_PATTERN = re.compile(
    r"\b(?:senior|sr|lead|principal|staff|architects?|managers?|head of|directors?|vice president|[as]?vp)\b",
    re.IGNORECASE,
)
ASSOCIATE_LEVEL_PATTERN = re.compile(r"(?:vice president\s*/|manager\s*[-–—,])\s*associate\b", re.IGNORECASE)


def _is_senior(title: str) -> bool:
    return bool(SENIOR_TITLE_PATTERN.search(title)) and not ASSOCIATE_LEVEL_PATTERN.search(title)


def _matches(raw: dict) -> bool:
    if str(raw["Id"]).endswith("_ORA_DELETED"):
        return False
    if _is_senior(raw["Title"]):
        return False
    return raw.get("JobFunction") in JOB_FUNCTIONS or is_core_title(raw["Title"])


def _location(raw: dict) -> str:
    places = [(raw.get("PrimaryLocationCountry"), raw.get("PrimaryLocation"))]
    places += [(s.get("CountryCode"), s.get("Name")) for s in raw.get("secondaryLocations") or []]
    names = [name for country in COUNTRIES for code, name in places if code == country and name]
    return "; ".join(dict.fromkeys(names))


def scrape() -> list[NormalizedJob]:
    return scrape_oracle_recruiting(
        name="JPMorgan Chase",
        host="jpmc.fa.oraclecloud.com",
        site_number="CX_1001",
        expand="requisitionList.secondaryLocations",
        finder_filters={"selectedLocationsFacet": f"{CANADA_FACET_ID};{US_FACET_ID}"},
        sort_by="POSTING_DATES_DESC",
        page_size=200,
        max_pages=75,
        min_complete=0.98,
        category_fn=lambda raw: raw.get("JobFunction") or "",
        job_filter=_matches,
        location_fn=_location,
    )
