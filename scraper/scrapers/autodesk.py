"""Autodesk careers scraper, scoped to Canada + tech job categories.

Autodesk has moved its careers site to **Eightfold** at
`jobs.autodesk.com/careers`, found 2026-09-25 (confirmed by `X-EF-*` response
headers). Its old Workday site (`autodesk.wd1.myworkdayjobs.com/Ext`) now
redirects to Workday's outage page and its CXS API reports the site ID as
not found, so it's no longer a usable source. autodesk.com itself is
Akamai-blocked, even to headless Chromium.

It uses the same Eightfold `pcsx` search API as Microsoft (scrapers/microsoft.py):
`GET https://jobs.autodesk.com/api/pcsx/search?domain=autodesk.com&query=&location=Canada&start=N`,
10 per page, with no auth (just a browser User-Agent).

- `location=Canada` is a real filter: 16 of 62 jobs worldwide on 2026-09-25.
- Category: unlike Microsoft's tenant, `department` here holds payroll-ish
  values ("Non-Commission", "Canada - Time Tracking"), so it's useless for
  scoping. The page's "Job Category" smart filter is the real facet,
  passed as a repeatable `filter_job_category` param (confirmed via the
  response's `appliedFilters.jobCategory`). Scope: "development
  engineering", "artificial intelligence", "cybersecurity", "technology"
  (7 Canadian jobs).
  - Internships are filed under a catch-all "intern fg" category covering
    all functions, so software co-ops in Montréal aren't included.
- `postedTs` is 0 on this tenant, so the posted date comes from
  `creationTs` (a Unix timestamp).
- Fields: `displayJobId` (= Workday-style req ID like "26WD100437",
  external_id), `name`, `locations[]` (often a long list of regional
  "AMER - Canada - <province> - Remote" variants — Canadian ones are shown),
  `positionUrl` (prefix with the site origin).
"""

from .base import NormalizedJob
from .eightfold import scrape_eightfold

JOB_CATEGORIES = ["development engineering", "artificial intelligence", "cybersecurity", "technology"]


def scrape() -> list[NormalizedJob]:
    return scrape_eightfold(
        name="Autodesk",
        base_url="https://jobs.autodesk.com",
        domain="autodesk.com",
        extra_params=[("filter_job_category", category) for category in JOB_CATEGORIES],
        category_label="Development Engineering / Technology",
    )
