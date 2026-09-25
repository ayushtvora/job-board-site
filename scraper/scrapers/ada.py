"""Ada (ada.cx) careers scraper, scoped to Canada + Product Development.

Greenhouse (board token `ada18`; `ada`/`adasupport` don't exist, found via
job-boards.greenhouse.io/ada18 links), via the shared helper in
scrapers/greenhouse.py. ada.cx itself is Cloudflare-403'd to plain HTTP.
Investigated 2026-09-25: 7 jobs, 6 in Canada (mostly "Remote - Canada").
Engineering sits under the "Product Development" department.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Ada", board_token="ada18", departments={"Product Development"})
