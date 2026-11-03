"""ApplyBoard careers scraper, scoped to Canada + tech roles (by title).

Workday CXS API, tenant `applyboard.wd3.myworkdayjobs.com/ApplyBoardNH`
(linked from applyboard.com/careers), via the shared helper in
scrapers/workday_cxs.py.

- `locationCountry` Canada = the shared `a30a87ed…` ID. Only 2 of 62 jobs
  on 2026-09-25 (Kitchener); most postings are overseas recruitment roles.
- This tenant has **no category facet at all**, so tech roles are picked by
  title keyword.
"""

import re

from .base import NormalizedJob, is_data_title
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
TECH_TITLE_PATTERN = re.compile(
    r"engineer|developer|software|data|machine learning|\bML\b|\bAI\b|security|devops|\bIT\b|platform", re.IGNORECASE
)


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="ApplyBoard",
        base_url="https://applyboard.wd3.myworkdayjobs.com",
        tenant="applyboard",
        site="ApplyBoardNH",
        applied_facets={"locationCountry": [CANADA_FACET_ID]},
        category_label="Technology",
        job_filter=lambda raw, _detail: bool(TECH_TITLE_PATTERN.search(raw["title"])) or is_data_title(raw["title"]),
    )
