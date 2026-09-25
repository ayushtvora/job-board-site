"""TELUS careers scraper, scoped to technology departments (currently none open).

`careers.telus.com` is SAP SuccessFactors' Jobs2Web layer (same as
Scotiabank/Rogers), via the shared helper in scrapers/jobs2web.py. Unlike
Rogers/Scotiabank there are no `/go/<category>/` landing pages — only the
generic `/search/` listing (paginated by `startrow`), and its department
facet dropdown is populated client-side — so every job (~152) is fetched
and filtered on the row's Department column.

**As of 2026-09-25 TELUS has zero technology postings on this board** —
its departments are Retail, Sales & Professional Services, Clinical /
Medical, Health Solutions, Customer Service, Administrative, Planning and
Analysis, and Co-op & Internship Programs; keyword searches for
"developer", "software", "engineer" all return only sales/retail/pharmacy
roles. Since the real tech department label can't be observed yet,
departments are matched by keyword — a legitimate empty result today, same
situation as Liberty Mutual/Riot. (`jobs.telusdigital.com` is TELUS
Digital, a separate subsidiary with its own board.)
"""

import re

from .base import NormalizedJob
from .jobs2web import scrape_jobs2web

TECH_DEPARTMENT_PATTERN = re.compile(
    r"technolog|engineer|software|develop|digital|data|information|\bIT\b", re.IGNORECASE
)


def scrape() -> list[NormalizedJob]:
    return scrape_jobs2web(
        name="TELUS",
        base_url="https://careers.telus.com",
        category_path=None,
        category_label="",
        department_filter=lambda department: bool(TECH_DEPARTMENT_PATTERN.search(department)),
    )
