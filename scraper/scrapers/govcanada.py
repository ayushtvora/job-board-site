"""Government of Canada careers scraper (federal tech jobs on GC Jobs).

Every tech posting on GC Jobs (see scrapers/gcjobs.py), except those from
organizations that have their own scraper here: Statistics Canada
(scrapers/statcan.py), the National Research Council (scrapers/nrc.py)
and the Bank of Canada (scrapers/bankofcanada.py). That way a posting
shows up once, under the most specific company. The job's category is the
hiring department or agency.
"""

from .base import NormalizedJob
from .gcjobs import scrape_gcjobs

SEPARATELY_TRACKED_ORGS = {"Statistics Canada", "National Research Council Canada", "Bank of Canada"}


def scrape() -> list[NormalizedJob]:
    return scrape_gcjobs(name="Government of Canada", org_filter=lambda org: org not in SEPARATELY_TRACKED_ORGS)
