"""University of Toronto careers scraper (staff postings, by title).

`jobs.utoronto.ca` is SAP SuccessFactors Jobs2Web, via scrapers/jobs2web.py.
Investigated 2026-11-10: 320 postings. The `/go/` category pages split by
employee group (Staff, Faculty, Librarian, CUPE 3902 teaching assistants,
...), not by field, so the "Staff Opportunities" page (75) is read and
scoped by title (`base.is_core_title`, plus IT/systems titles); the
keyword searches find data roles in the other groups. Teaching and
faculty postings (professor, lecturer, ...) are left out, even with a
data title.
"""

import re

from .base import NormalizedJob, is_core_title
from .jobs2web import scrape_jobs2web

FACULTY_TITLE_PATTERN = re.compile(r"professor|lecturer|instructor|teaching|faculty|postdoc", re.IGNORECASE)
TECH_TITLE_PATTERN = re.compile(r"\bIT\b|information technology|systems? (?:analyst|admin)|database|cyber|architect", re.IGNORECASE)


def scrape() -> list[NormalizedJob]:
    return scrape_jobs2web(
        name="University of Toronto",
        base_url="https://jobs.utoronto.ca",
        category_path="/go/Staff-Opportunities/2607517",
        category_label="Staff",
        job_filter=lambda job: (is_core_title(job["title"]) or bool(TECH_TITLE_PATTERN.search(job["title"])))
        and not FACULTY_TITLE_PATTERN.search(job["title"]),
    )
