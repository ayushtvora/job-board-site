"""Intact Financial careers scraper, scoped to Canada + Information Technology / Data Management.

`careers.intactfc.com` is a custom listing front-end (its `/api/jobs` is
Akamai-403'd to plain HTTP), but every job's apply link points at Workday —
tenant `intactfc.wd3.myworkdayjobs.com/intactfc` — and that tenant's CXS API
is open. Via the shared helper in scrapers/workday_cxs.py.

- Category facet `jobFamilyGroup`: "Information Technology" =
  `614baa0178de10010db4079734c50000`, "Data Management" =
  `614baa0178de10010db40530706e0000`.
- **No country facet** on this tenant — only a flat `locations` facet of
  ~38 office/city values. All are Canadian except "Hong Kong Science Park,
  HK" (confirmed 2026-09-25), so Canada is filtered client-side on the
  detail endpoint's `country.descriptor` instead of listing every city ID.
- Postings are bilingual; some titles are French-only (e.g.
  "Développeur·se ..."), straight from the source.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CATEGORY_FACET_IDS = [
    "614baa0178de10010db4079734c50000",  # Information Technology
    "614baa0178de10010db40530706e0000",  # Data Management
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Intact",
        base_url="https://intactfc.wd3.myworkdayjobs.com",
        tenant="intactfc",
        site="intactfc",
        applied_facets={"jobFamilyGroup": CATEGORY_FACET_IDS},
        category_label="Information Technology",
        job_filter=_is_canada,
    )


def _is_canada(_raw: dict, detail: dict) -> bool:
    return (detail.get("country") or {}).get("descriptor") == "Canada"
