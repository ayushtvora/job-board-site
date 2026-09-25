"""Interac careers scraper, scoped to IT + Software Engineering.

Workday CXS API, tenant `interac.wd3.myworkdayjobs.com/Interac` (linked
from interac.ca's careers page), via the shared helper in
scrapers/workday_cxs.py.

- Category facet `jobFamilyGroup`: "Software Engineering" =
  `64190eb17ad210012ee3b9b8b0e60000`, "IT" = `64190eb17ad210012ee3b4522c710000`
  (23 jobs combined, 2026-09-25).
- No country facet needed: the only `locations` values are "Toronto" and
  "Quebec" — Interac is Canadian-only.
- The tenant also hosts Interac's subsidiary 2Keys Corporation (a
  `hiringCompany` facet value); not filtered out, since its roles are
  Canadian tech jobs too.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CATEGORY_FACET_IDS = [
    "64190eb17ad210012ee3b9b8b0e60000",  # Software Engineering
    "64190eb17ad210012ee3b4522c710000",  # IT
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Interac",
        base_url="https://interac.wd3.myworkdayjobs.com",
        tenant="interac",
        site="Interac",
        applied_facets={"jobFamilyGroup": CATEGORY_FACET_IDS},
        category_label="Software Engineering / IT",
    )
