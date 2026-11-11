"""University Health Network (UHN) careers scraper (Technology and Data & Analytics portfolios).

SmartRecruiters, company `UniversityHealthNetwork`, via
scrapers/smartrecruiters.py. `country=ca` filters server-side.
Investigated 2026-11-10: 184 postings, mostly clinical. Scope is the "VP
Portfolio" custom field's "Technology and Innovation" and "Data &
Analytics" values (8 postings), plus data/software titles anywhere (UHN's
research institutes post data analysts and bioinformaticians under
"Science & Research").
"""

from .base import NormalizedJob
from .smartrecruiters import scrape_smartrecruiters


def scrape() -> list[NormalizedJob]:
    return scrape_smartrecruiters(
        name="UHN",
        company="UniversityHealthNetwork",
        field_label="VP Portfolio",
        field_values={"Technology and Innovation", "Data & Analytics"},
    )
