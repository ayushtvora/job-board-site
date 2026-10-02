"""National Research Council Canada careers scraper (tech jobs on GC Jobs).

The NRC posts its jobs on GC Jobs (see scrapers/gcjobs.py), titles
suffixed with its own competition number (e.g. "Data Scientist (#26120)").
27 NRC postings on 2026-10-02; this keeps the ones with tech titles
(developers, data scientists, systems engineers).
"""

from .base import NormalizedJob
from .gcjobs import scrape_gcjobs


def scrape() -> list[NormalizedJob]:
    return scrape_gcjobs(name="National Research Council Canada", org_filter=lambda org: org == "National Research Council Canada")
