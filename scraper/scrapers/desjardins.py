"""Desjardins careers scraper, scoped to Information technology / Security / Data.

Workday CXS API, tenant `desjardins.wd10.myworkdayjobs.com/Desjardins`, via
the shared helper in scrapers/workday_cxs.py.

- Category facet `jobFamilyGroup`: "Information technology (FG)",
  "Security (FG)", "Data (FG)" (23 of 277 jobs, 2026-09-25).
- No country filter needed: every `Region` value is a Canadian province
  (mostly Québec, some Ontario).
- Many postings are French-only; titles are kept as posted.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CATEGORY_FACET_IDS = [
    "2af490494b0c01d3bba6e41b706aed5f",  # Information technology (FG)
    "416804d155e11011e56e07a4c79e0000",  # Security (FG)
    "f3d214e2769b0170aeb959779f1f6e1f",  # Data (FG)
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Desjardins",
        base_url="https://desjardins.wd10.myworkdayjobs.com",
        tenant="desjardins",
        site="Desjardins",
        applied_facets={"jobFamilyGroup": CATEGORY_FACET_IDS},
        category_label="Information technology",
    )
