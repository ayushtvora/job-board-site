"""EY careers scraper (Canada / technology roles).

careers.ey.com/ey is SuccessFactors Jobs2Web (same layer as Scotiabank,
Rogers and Canada Life), via scrapers/jobs2web.py in `/search/` mode.

- `optionsFacetsDD_country=CA` is a real server-side filter (345 Canadian
  jobs on 2026-10-02). The service-line facet (`optionsFacetsDD_customfield1`)
  accepts "Consulting" (108) but its other values are loaded by AJAX and
  weren't found, and the listing has no department column.
- So scope is all Canadian postings filtered by title: technology,
  software, data, cloud, cyber, AI and engineering roles. Titles are the
  only per-job signal here, so this is a heuristic (it can include e.g. a
  "Technology Risk" auditor). Tax titles are excluded: EY's SR&ED
  practice posts "Tax Staff - IT" roles that are tax work, not IT work.
- `/ey` is a path prefix; job links like `/ey/job/<slug>/<id>/`
  are resolved against the site root.
"""

import re

from .base import NormalizedJob, is_data_title
from .jobs2web import scrape_jobs2web

TITLE_PATTERN = re.compile(
    r"technolog|software|developer|engineer|data|cloud|cyber|\bAI\b|artificial intelligence|machine learning|"
    r"architect|devops|\bIT\b|digital|automation|salesforce|servicenow|\bSAP\b|technologie|logiciel|donn[ée]es",
    re.IGNORECASE,
)
EXCLUDE_PATTERN = re.compile(r"\btax\b|fiscalit", re.IGNORECASE)


def scrape() -> list[NormalizedJob]:
    return scrape_jobs2web(
        name="EY",
        base_url="https://careers.ey.com/ey",
        category_path=None,
        category_label="Technology (title match)",
        search_params={"optionsFacetsDD_country": "CA"},
        job_filter=lambda job: bool(TITLE_PATTERN.search(job["title"]) or is_data_title(job["title"]))
        and not EXCLUDE_PATTERN.search(job["title"]),
    )
