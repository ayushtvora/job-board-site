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

import logging
import re

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://ehtc.fa.ca2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
SITE_NUMBER = "CX_1"
EXPAND = "requisitionList.secondaryLocations,flexFieldsFacet.values"
FACETS_LIST = "LOCATIONS;WORK_LOCATIONS;TITLES;CATEGORIES;ORGANIZATIONS;POSTING_DATES;FLEX_FIELDS"

PAGE_SIZE = 25
MAX_PAGES = 20  # safety cap; site currently has ~38 total jobs

# CLAUDE.md's recommended keyword list for spotting IT-adjacent titles at a
# site with no real tech/IT category facet. "IT" alone is matched as a
# whole word only, to avoid false positives like "Administrative" or
# "Visit".
_KEYWORD_PATTERN = re.compile(r"I&IT|\bIT\b|Software|Developer|Systems", re.IGNORECASE)


def scrape() -> list[NormalizedJob]:
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    offset = 0
    total: int | None = None

    with httpx.Client(timeout=30) as client:
        for _ in range(MAX_PAGES):
            finder = (
                f"findReqs;siteNumber={SITE_NUMBER},"
                f"facetsList={FACETS_LIST},"
                f"limit={PAGE_SIZE},offset={offset},sortBy=POSTING_DATES_DESC"
            )
            response = client.get(
                BASE_URL,
                params={
                    "onlyData": "true",
                    "expand": EXPAND,
                    "finder": finder,
                },
            )
            response.raise_for_status()
            item = response.json()["items"][0]

            # Only trust `total` from the first page — same convention as
            # the Workday scrapers' TD-bug fix.
            if total is None:
                total = item.get("TotalJobsCount", 0)
            requisitions = item.get("requisitionList") or []
            if not requisitions:
                break

            for raw in requisitions:
                job_id = str(raw["Id"])
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                title = raw.get("Title", "")
                match = _KEYWORD_PATTERN.search(title)
                if not match:
                    continue
                jobs.append(_normalize(raw, match.group(0)))

            offset += PAGE_SIZE
            if offset >= total:
                break
        else:
            logger.warning("Metrolinx scrape hit MAX_PAGES=%d without finishing — got %d jobs", MAX_PAGES, len(jobs))

    logger.info(
        "Metrolinx: fetched %d IT-adjacent jobs (site reported total=%s before keyword filter)",
        len(jobs),
        total,
    )
    return jobs


def _normalize(raw: dict, matched_keyword: str) -> NormalizedJob:
    return {
        "external_id": str(raw["Id"]),
        "title": raw["Title"],
        "url": f"https://ehtc.fa.ca2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/{SITE_NUMBER}/job/{raw['Id']}",
        "location": raw.get("PrimaryLocation", ""),
        "category": matched_keyword,
        "posted_date": raw.get("PostedDate"),
        "platform": "Oracle Recruiting Cloud",
    }
