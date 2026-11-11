"""City of Toronto careers scraper, scoped to the Information & Technology job stream.

`jobs.toronto.ca/jobsatcity` is SAP SuccessFactors Jobs2Web (the newer
job-tile template, same as ATS Corporation), via the shared helper in
scrapers/jobs2web.py. There are no `/go/` category pages, so everything is
fetched from `/search/` (72 jobs, 2026-09-25).

The tile's "department" field is labelled "Job Stream" here;
"Information & Technology" is the tech stream (9 jobs). About 20 tiles had
no stream at all, so those are kept when the title looks like a tech role.
The tiles have no location field (every job is the City's own), so
location is set to "Toronto, ON".
"""

import re

from .base import NormalizedJob, is_core_title
from .jobs2web import scrape_jobs2web

TECH_TITLE_PATTERN = re.compile(
    r"software|developer|\bIT\b|information technology|data|cyber|security|cloud|architect|devops|digital|systems",
    re.IGNORECASE,
)


def scrape() -> list[NormalizedJob]:
    jobs = scrape_jobs2web(
        name="City of Toronto",
        base_url="https://jobs.toronto.ca/jobsatcity",
        category_path=None,
        category_label="",
        job_filter=_keep,
    )
    return [{**job, "location": job["location"] or "Toronto, ON"} for job in jobs]


def _keep(job: NormalizedJob) -> bool:
    if is_core_title(job["title"]):
        return True
    if job["category"]:
        return job["category"] == "Information & Technology"
    return bool(TECH_TITLE_PATTERN.search(job["title"]))
