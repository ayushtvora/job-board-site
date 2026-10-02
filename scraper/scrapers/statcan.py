"""Statistics Canada careers scraper (tech jobs on GC Jobs).

Statistics Canada hires through GC Jobs (see scrapers/gcjobs.py); this
keeps its postings with tech titles. On 2026-10-02 it had 4 postings, all
data-collection clerks, so an empty result is expected for now.
"""

from .base import NormalizedJob
from .gcjobs import scrape_gcjobs


def scrape() -> list[NormalizedJob]:
    return scrape_gcjobs(name="Statistics Canada", org_filter=lambda org: org == "Statistics Canada")
