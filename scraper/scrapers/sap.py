"""SAP careers scraper (Canada / Software-Design and Development jobs).

**Re-investigated 2026-10-02**: jobs.sap.com was rebuilt as a Next.js app
(Vercel, behind Cloudflare). The old Jobs2Web `/search/` page this scraper
used to parse now 301s to `/en/jobs/` (and 403s plain httpx), so SAP's jobs
now come from two separate backends:

- **SAP SuccessFactors classic RCM XML feed**, which holds SAP's main job set
  (769 postings worldwide, 10 in Canada on 2026-10-02; new postings still
  appearing daily):
  `GET https://career5.successfactors.eu/career?company=SAP&career_ns=job_listing_summary&resultType=XML`.
  This is the same feed as Canada Life's and ATS Corporation's, but SAP's
  includes the custom fields: each `<Job>` has `ReqId`, `JobTitle`,
  `Posted-Date` (MM/DD/YYYY) and `<filterN><label>/<value>` pairs, among them
  "Work Area" (e.g. "Software-Design and Development"), "Country" and
  "Internal Posting Location" (city). It's one ~11 MB response, with no
  pagination or server-side filtering. It isn't reliably well-formed XML
  (see scrapers/canadalife.py), so it's parsed with regexes per `<Job>`.
  These jobs aren't on the new jobs.sap.com (`/en/jobs/<ReqId>/` 404s), but
  the classic job page
  `career5.successfactors.eu/career?company=SAP&career_ns=job_listing&career_job_req_id=<ReqId>`
  renders the posting with a working Apply button, so that's the URL used.
- **SmartRecruiters**, company `SAPITBusinessSysteme`. That's what the new
  jobs.sap.com actually lists (51 postings worldwide, all under the "SAP IT
  Business Systeme" entity; each job page's `applicationUrl` points at
  `jobs.smartrecruiters.com/SAPITBusinessSysteme/...`). This set doesn't
  overlap with the SuccessFactors feed. It's scoped by the "Board Area"
  custom field, where "Product & Engineering" is the closest match to
  "Software-Design and Development". There were 0 matching Canada postings
  on 2026-10-02. It's scraped too in case SAP moves more postings over.

`platform` is `"SuccessFactors"` or `"SmartRecruiters"` per source.
"""

import html
import logging
import re
from datetime import datetime

import httpx

from .base import NormalizedJob, is_data_title
from .smartrecruiters import scrape_smartrecruiters

logger = logging.getLogger(__name__)

FEED_URL = "https://career5.successfactors.eu/career"
FEED_PARAMS = {"company": "SAP", "career_ns": "job_listing_summary", "resultType": "XML"}
JOB_URL = "https://career5.successfactors.eu/career?company=SAP&career_ns=job_listing&career_job_req_id={}"
WORK_AREAS = {"Software-Design and Development"}

SMARTRECRUITERS_COMPANY = "SAPITBusinessSysteme"
SMARTRECRUITERS_BOARD_AREAS = {"Product & Engineering"}

JOB_RE = re.compile(r"<Job>(.*?)</Job>", re.DOTALL)
FILTER_RE = re.compile(r"<label>(.*?)</label>\s*<value>(.*?)</value>", re.DOTALL)
CDATA_RE = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)


def scrape() -> list[NormalizedJob]:
    jobs = _scrape_successfactors()
    jobs += scrape_smartrecruiters(
        name="SAP",
        company=SMARTRECRUITERS_COMPANY,
        field_label="Board Area",
        field_values=SMARTRECRUITERS_BOARD_AREAS,
    )
    return jobs


def _scrape_successfactors() -> list[NormalizedJob]:
    with httpx.Client(timeout=60) as client:
        response = client.get(FEED_URL, params=FEED_PARAMS)
        response.raise_for_status()

    postings = JOB_RE.findall(response.text)
    if not postings:
        # The feed answers 200 with an HTML page for an unknown company, so an
        # empty parse means the feed moved, not that SAP has no jobs.
        raise RuntimeError("SAP SuccessFactors feed returned no <Job> elements")

    jobs: list[NormalizedJob] = []
    for posting in postings:
        fields = {label.strip(): html.unescape(value.strip()) for label, value in FILTER_RE.findall(posting)}
        title = _tag(posting, "JobTitle")
        if fields.get("Work Area") not in WORK_AREAS and not is_data_title(title):
            continue
        if fields.get("Country") != "Canada" and "Canada" not in fields.get("Additional Locations", ""):
            continue

        req_id = _tag(posting, "ReqId")
        city = fields.get("Internal Posting Location", "")
        jobs.append(
            {
                "external_id": req_id,
                "title": title,
                "url": JOB_URL.format(req_id),
                "location": f"{city}, Canada" if city else "Canada",
                "category": fields.get("Work Area", ""),
                "posted_date": _parse_date(_tag(posting, "Posted-Date")),
                "platform": "SuccessFactors",
            }
        )

    logger.info("SAP: %d of %d SuccessFactors postings matched Canada + %s", len(jobs), len(postings), WORK_AREAS)
    return jobs


def _tag(posting: str, name: str) -> str:
    match = re.search(rf"<{name}>(.*?)</{name}>", posting, re.DOTALL)
    if match is None:
        return ""
    value = match.group(1)
    cdata = CDATA_RE.search(value)
    return html.unescape(cdata.group(1) if cdata else value).strip()


def _parse_date(text: str) -> str | None:
    try:
        return datetime.strptime(text, "%m/%d/%Y").date().isoformat()
    except ValueError:
        return None
