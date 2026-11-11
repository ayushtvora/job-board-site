"""ICBC careers scraper (Information Services, plus data/software titles).

`careers.icbc.com` is SAP SuccessFactors Jobs2Web, via scrapers/jobs2web.py.
Investigated 2026-11-10: `/go/` category pages include
"Information-Services" (3 postings) and "Actuary-&-Analytics" (11, where
ICBC's data scientists and engineers sit); the latter's data roles come
from the helper's keyword searches. All postings are in BC (North
Vancouver head office, Surrey, Burnaby).
"""

from .base import NormalizedJob
from .jobs2web import scrape_jobs2web


def scrape() -> list[NormalizedJob]:
    return scrape_jobs2web(
        name="ICBC",
        base_url="https://careers.icbc.com",
        category_path="/go/Information-Services/2682817",
        category_label="Information Services",
    )
