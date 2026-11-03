"""Bank of Canada careers scraper, scoped to IT roles (by title).

`careers.bankofcanada.ca` is SAP SuccessFactors Jobs2Web, via the shared
helper in scrapers/jobs2web.py. Only 14 jobs on 2026-09-25, all Ottawa or
Toronto, with one `/go/All-Job-Opportunities/` page and no category or
Department column, so IT roles are picked by title keyword.

The table's date column is the **closing** date, not a posted date. The
helper only reads a `.jobDate` column, which this site doesn't have, so
`posted_date` is None and the UI falls back to first-seen, as intended.
"""

import re

from .base import NormalizedJob, is_data_title
from .jobs2web import scrape_jobs2web

TECH_TITLE_PATTERN = re.compile(
    r"software|developer|\bIT\b|information technology|data|cyber|security|cloud|architect|devops|endpoint|"
    r"network|infrastructure|engineer",
    re.IGNORECASE,
)


def scrape() -> list[NormalizedJob]:
    return scrape_jobs2web(
        name="Bank of Canada",
        base_url="https://careers.bankofcanada.ca",
        category_path=None,
        category_label="Information Technology",
        job_filter=lambda job: bool(TECH_TITLE_PATTERN.search(job["title"])) or is_data_title(job["title"]),
    )
