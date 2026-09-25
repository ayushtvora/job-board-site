"""Clio careers scraper, scoped to Canada + Engineering.

clio.com itself is Cloudflare-403'd to plain HTTP, but its job postings
live on Workday — tenant `clio.wd3.myworkdayjobs.com/ClioCareerSite` (found
via public job links) — whose CXS API is open. Via the shared helper in
scrapers/workday_cxs.py.

- Category facet `jobFamilyGroup`, "Engineering" =
  `29827a73287b0103383979088de50000` (31 jobs, 2026-09-25).
- **No country facet** — only a `locations` facet with city/remote values
  (e.g. two separate "Remote - Canada" IDs, "Remote - Italy", ...).
  Canada is filtered client-side on the detail endpoint's
  `country.descriptor`, same as Intact.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CATEGORY_FACET_ID = "29827a73287b0103383979088de50000"  # Engineering


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Clio",
        base_url="https://clio.wd3.myworkdayjobs.com",
        tenant="clio",
        site="ClioCareerSite",
        applied_facets={"jobFamilyGroup": [CATEGORY_FACET_ID]},
        category_label="Engineering",
        job_filter=_is_canada,
    )


def _is_canada(_raw: dict, detail: dict) -> bool:
    return (detail.get("country") or {}).get("descriptor") == "Canada"
