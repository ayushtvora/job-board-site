"""Arctic Wolf careers scraper, scoped to Canada + R&D / IT / Security Services.

arcticwolf.com's careers page links to Workday — tenant
`arcticwolf.wd1.myworkdayjobs.com/External` — via the shared helper in
scrapers/workday_cxs.py.

- Category facet `jobFamilyGroup`: "R&D (RD)" =
  `f6cfbd603ca11001ed8fdbe0fca80000`, "IT & Operations (IT)" =
  `f6cfbd603ca11001ed8fd7111a630000`, "Security Services (S2)" =
  `e3a7c80f96c110014c11fae52d250000` (Arctic Wolf's SOC/security-engineering
  org — its core technical function as a security company).
- **No country facet** — only a `locations` facet mixing offices and
  "Remote, <country>" values (Canada appears as "Waterloo, ON, CAN",
  "Office - CAN - Ontario, Waterloo", "Remote, Canada", "Remote - CAN -
  Alberta"). Canada is filtered client-side on the detail endpoint's
  `country.descriptor`, same as Intact/Clio, so new Canadian location
  values are picked up automatically.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CATEGORY_FACET_IDS = [
    "f6cfbd603ca11001ed8fdbe0fca80000",  # R&D (RD)
    "f6cfbd603ca11001ed8fd7111a630000",  # IT & Operations (IT)
    "e3a7c80f96c110014c11fae52d250000",  # Security Services (S2)
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Arctic Wolf",
        base_url="https://arcticwolf.wd1.myworkdayjobs.com",
        tenant="arcticwolf",
        site="External",
        applied_facets={"jobFamilyGroup": CATEGORY_FACET_IDS},
        category_label="R&D / IT / Security Services",
        job_filter=_is_canada,
    )


def _is_canada(_raw: dict, detail: dict) -> bool:
    return (detail.get("country") or {}).get("descriptor") == "Canada"
