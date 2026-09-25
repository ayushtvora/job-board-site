"""Sony careers scraper, scoped to Canada + Product Development (Software).

Same Workday CXS API approach as SOTI (scrapers/soti.py) — see that module's
docstring for how this pattern works in general. Sony-specific notes:

- Sony's own corporate careers page is flat-blocked (Akamai); the real
  public careers site is `sonyjobs.com`, which embeds an iframe pointing at
  Sony's Workday tenant. Tenant/site:
  `sonyglobal.wd1.myworkdayjobs.com/SonyGlobalCareers`.
- Country facet is `locationCountry`, value
  `a30a87ed25634629aa6c3958aa2b91ea` = "Canada" — the same shared
  cross-tenant ID already seen on SOTI/CIBC/TD/Manulife.
- Category facet is `jobFamilyGroup`, value
  `bf0e94cb2dac0126e6d1bfd19e01df13` = "Product Development_Software" — a
  specific sub-group distinct from a broader parent "Product Development"
  facet.
- **This exact combination currently returns 0 jobs** (confirmed: a
  Canada-only search finds 1 unrelated marketing role, so this is a real,
  legitimate empty result for the Software Engineering slice, not a bug —
  do not loosen the filter to compensate).
- `bulletFields` structure not otherwise confirmed distinct from SOTI/CIBC's
  single-element case, so `category` is hardcoded to the filtered facet's
  label, same reasoning as SOTI.
- Posted date and canonical apply URL: same as SOTI, from each job's detail
  endpoint (`jobPostingInfo.startDate` / `.externalUrl`).
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

# Opaque Workday facet IDs, not derivable from their labels — confirmed
# against the site's own facet metadata (see module docstring).
CATEGORY_FACET_ID = "bf0e94cb2dac0126e6d1bfd19e01df13"  # Product Development_Software
COUNTRY_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"  # Canada


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Sony",
        base_url="https://sonyglobal.wd1.myworkdayjobs.com",
        tenant="sonyglobal",
        site="SonyGlobalCareers",
        applied_facets={"jobFamilyGroup": [CATEGORY_FACET_ID], "locationCountry": [COUNTRY_FACET_ID]},
        category_label="Product Development - Software",
    )
