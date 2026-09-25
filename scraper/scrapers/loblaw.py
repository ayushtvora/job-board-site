"""Loblaw Digital careers scraper (all postings).

Workday CXS API, tenant `myview` (Loblaw's shared tenant), site
`Loblaw-Digital_Careers_Carrieres`, via the shared helper in
scrapers/workday_cxs.py. careers.loblaw.ca and loblawdigital.co link here.

- The site is Loblaw Digital's own (engineering, product, data, design),
  so no category facet is applied. Everything is Toronto/Brampton.
- **Empty as of 2026-09-25**: the site (and the corporate `loblaw_careers`
  site) returned 0 postings, not an error; the tenant and site ID were
  confirmed from the page's own `window.workday` config. Same "legitimately
  empty for now" situation as TELUS.
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="Loblaw Digital",
        base_url="https://myview.wd3.myworkdayjobs.com",
        tenant="myview",
        site="Loblaw-Digital_Careers_Carrieres",
        applied_facets={},
        category_label="Loblaw Digital",
    )
