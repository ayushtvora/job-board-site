"""CIBC careers scraper, scoped to Canada + Information Technology.

Same Workday CXS API approach as SOTI (scrapers/soti.py) — see that module's
docstring for how this pattern works in general. CIBC-specific notes:

- Tenant/site: `cibc.wd3.myworkdayjobs.com/search` (the "site" segment is
  `search`, not `Careers` as in SOTI's case — this varies per tenant and is
  just read off the site's own URL).
- Facet parameter names are `jobFamilyGroup` (Job Category) and `Country`,
  confirmed against the site's own facet metadata: `jobFamilyGroup`
  value `4bbe6c74e8a70126f29430a881012510` = "Information Technology",
  `Country` value `a30a87ed25634629aa6c3958aa2b91ea` = "Canada" — the same
  opaque Canada ID SOTI's job detail responses used, suggesting Workday
  reuses common reference IDs (like countries) across tenants.
- Unlike SOTI, `bulletFields` here is just `[reqId]` — no second field with
  a more specific category — so `category` is hardcoded to the filtered
  facet's label, same reasoning as SOTI's category.
- Posted date and canonical apply URL: same as SOTI, from each job's detail
  endpoint (`jobPostingInfo.startDate` / `.externalUrl`).
- Co-ops, internships and new-grad programs are on a second site,
  `cibc.wd3.myworkdayjobs.com/campus` (found 2026-11-10 by probing common
  site names; 45 Canadian postings, ~25 of them tech or data, all
  Toronto). Its job families are "Students and Rotational Programs" etc.,
  so it's scoped by title (`base.is_core_title`). Some campus postings are
  on the main site too under the same req ID, so results are de-duplicated.
"""

from .base import NormalizedJob, is_core_title
from .workday_cxs import scrape_workday

# Opaque Workday facet IDs, not derivable from their labels — confirmed
# against the site's own facet metadata (see module docstring).
CATEGORY_FACET_ID = "4bbe6c74e8a70126f29430a881012510"  # Information Technology
COUNTRY_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"  # Canada


def scrape() -> list[NormalizedJob]:
    jobs: dict[str, NormalizedJob] = {}
    for job in scrape_workday(
        name="CIBC",
        base_url="https://cibc.wd3.myworkdayjobs.com",
        tenant="cibc",
        site="search",
        applied_facets={"jobFamilyGroup": [CATEGORY_FACET_ID], "Country": [COUNTRY_FACET_ID]},
        category_label="Information Technology",
    ) + scrape_workday(
        # Co-ops, internships and new-grad programs (45 Canadian postings on
        # 2026-11-10). Its job families are "Students and Rotational
        # Programs" and the like, so scope is by title.
        name="CIBC (Campus)",
        base_url="https://cibc.wd3.myworkdayjobs.com",
        tenant="cibc",
        site="campus",
        applied_facets={"Country": [COUNTRY_FACET_ID]},
        category_label="Campus",
        job_filter=lambda raw, _detail: is_core_title(raw["title"]),
    ):
        # Many campus postings are on the main site too, with the same req ID.
        jobs.setdefault(job["external_id"], job)
    return list(jobs.values())
