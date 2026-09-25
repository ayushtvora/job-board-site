"""CAE careers scraper, scoped to Canada + engineering / IT.

Workday CXS API, tenant `cae.wd3.myworkdayjobs.com/career` (linked from
cae.com/careers), via the shared helper in scrapers/workday_cxs.py.

- `Location_Country` Canada = the shared `a30a87ed…` ID (94 of 349 jobs,
  2026-09-25; mostly Montréal / Saint-Laurent, some Ottawa and Toronto).
- Category facet `jobFamilyGroup`: "Engineering and Product Development",
  "IT & Telecommunications", "Digital Accelerator". The large "Training ..."
  groups are flight-instructor roles, so they're left out.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
CATEGORY_FACET_IDS = [
    "753eebcc39364bd8bed50db6d8e71f32",  # Engineering and Product Development
    "d695e586ffc04d1cbfae0d2f51e2f64a",  # IT & Telecommunications
    "e8a95027dd2801963bc54d595a52454d",  # Digital Accelerator
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="CAE",
        base_url="https://cae.wd3.myworkdayjobs.com",
        tenant="cae",
        site="career",
        applied_facets={"jobFamilyGroup": CATEGORY_FACET_IDS, "Location_Country": [CANADA_FACET_ID]},
        category_label="Engineering and Product Development",
    )
