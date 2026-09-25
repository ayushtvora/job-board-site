"""Nvidia careers scraper, scoped to Canada + Engineering.

Same Workday CXS API approach as SOTI (scrapers/soti.py) — see that module's
docstring for how this pattern works in general. Nvidia-specific notes:

- Tenant/site: `nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite`.
- Category facet is `jobFamilyGroup`, value `0c40f6bd1d8f10ae43ffaefd46dc7e78`
  = "Engineering".
- **Country is not a flat facet here** (unlike SOTI/CIBC/TD/Manulife's
  `Country`/`Location_Country`) — it's nested under a `locationHierarchy1`
  facet (itself under a `locationMainGroup` facet group in the site's own
  facet metadata), value `2fcb99c455831013ea529c3b93ba3236` = "Canada" — a
  tenant-specific ID, *not* the shared `a30a87ed25634629aa6c3958aa2b91ea`
  used elsewhere, confirming each tenant's facet IDs need independent
  verification even when the facet *parameter name* (`locationCountry`
  Sony/SOTI/CIBC/TD vs. `locationHierarchy1` here) differs too.
- Combined `appliedFacets: {"jobFamilyGroup": [...], "locationHierarchy1": [...]}`
  confirmed working: 10 real Canada + Engineering jobs.
- `bulletFields` is single-element here (`[reqId]`, no second field like
  TD/Manulife) — so `category` is hardcoded to the filtered facet's label.
- Posted date and canonical apply URL: same as SOTI, from each job's detail
  endpoint (`jobPostingInfo.startDate` / `.externalUrl`).
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

# Opaque Workday facet IDs, not derivable from their labels — confirmed
# against the site's own facet metadata (see module docstring).
CATEGORY_FACET_ID = "0c40f6bd1d8f10ae43ffaefd46dc7e78"  # Engineering
COUNTRY_FACET_ID = "2fcb99c455831013ea529c3b93ba3236"  # Canada (tenant-specific, not the shared cross-tenant ID)


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Nvidia",
        base_url="https://nvidia.wd5.myworkdayjobs.com",
        tenant="nvidia",
        site="NVIDIAExternalCareerSite",
        applied_facets={"jobFamilyGroup": [CATEGORY_FACET_ID], "locationHierarchy1": [COUNTRY_FACET_ID]},
        category_label="Engineering",
    )
