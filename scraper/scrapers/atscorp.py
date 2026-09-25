"""ATS Corporation (atsautomation.com) careers scraper, scoped to Canada + Engineering.

Unblocked 2026-09-25. The earlier investigation stopped at
`career5.successfactors.eu/career?company=atsP2` (SuccessFactors classic
RCM, an AJAX/session-driven search). But the RCM's public XML feed
(`career?company=atsP2&career_ns=job_listing_summary&resultType=XML`, the
same one found for Canada Life) links each job to a **Jobs2Web** page on
`jobs.atsautomation.com`, and that site's category pages are plain
server-rendered HTML. Uses the shared helper in scrapers/jobs2web.py.

- Category page: `/go/Engineering%2C-Design%2C-&-Technical-Services/4455701/`
  (~296 jobs worldwide). A separate `/PA/` path is a second branded site
  for ATS's German business, with its own copy of the category.
- It uses the tile template (`li.job-tile`, with labeled country /
  department / location / date fields), not the table template, and has no
  results-count marker. The helper handles both.
- Canada is filtered client-side on location (e.g. "Cambridge, ON, CA,
  N3H 4R7"). That was 22 jobs, mostly "Engineering and Design", on
  2026-09-25.
- `platform` = "SuccessFactors".
"""

from .base import CANADA_PATTERN, NormalizedJob
from .jobs2web import scrape_jobs2web


def scrape() -> list[NormalizedJob]:
    return scrape_jobs2web(
        name="ATS Corporation",
        base_url="https://jobs.atsautomation.com",
        category_path="/go/Engineering%2C-Design%2C-%26-Technical-Services/4455701",
        category_label="Engineering, Design, & Technical Services",
        job_filter=lambda job: bool(CANADA_PATTERN.search(job["location"])),
    )
