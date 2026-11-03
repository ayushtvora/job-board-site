"""RBC careers scraper (Technology | Analytics | Research category).

The site (Phenom People's Career Site Builder) looks JS-rendered, but each
page's job results are actually embedded server-side in a `phApp.ddo = {...}`
JSON assignment inside a <script> tag — no browser/JS execution needed, a
plain HTTP GET is enough. See CLAUDE.md's "RBC scraping approach" section
for how this was found.
"""

from .base import NormalizedJob
from .phenom import scrape_phenom


def scrape() -> list[NormalizedJob]:
    return scrape_phenom(
        name="RBC",
        list_url="https://jobs.rbc.com/ca/en/c/technology-analytics-research-jobs",
        params={"s": 1},
        search_url="https://jobs.rbc.com/ca/en/search-results",
        platform="Workday",
    )
