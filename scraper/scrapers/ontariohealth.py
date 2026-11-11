"""Ontario Health careers scraper (tech and data roles, by title).

Workday CXS API, tenant `oh.wd3.myworkdayjobs.com/OH`, via
scrapers/workday_cxs.py. Investigated 2026-11-10: only 19 postings, all in
Ontario. Ontario Health's careers page said in February 2026 that
recruitment is paused under the provincial hiring freeze, so expect few.

- No category facet at all, so every posting is read and scoped by title
  (`base.is_core_title`, plus architect/IT titles like "Lead Architect,
  Network").
"""

import re

from .base import NormalizedJob, is_core_title
from .workday_cxs import scrape_workday

TECH_TITLE_PATTERN = re.compile(r"architect|\bIT\b|information technology|cyber|network|systems? (?:analyst|admin)", re.IGNORECASE)


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Ontario Health",
        base_url="https://oh.wd3.myworkdayjobs.com",
        tenant="oh",
        site="OH",
        applied_facets={},
        category_label="Title match",
        job_filter=lambda raw, _detail: is_core_title(raw["title"]) or bool(TECH_TITLE_PATTERN.search(raw["title"])),
    )
