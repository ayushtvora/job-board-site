"""NielsenIQ careers scraper (Canada, technology and data job families).

SmartRecruiters, company `NielsenIQ` (nielseniq.com/global/en/careers links
to it), via scrapers/smartrecruiters.py. `country=ca` filters server-side.
Investigated 2026-11-10: 418 postings worldwide, only 1 in Canada (Toronto,
customer success). Scope is the "Job Family Group" custom field's tech and
data values, plus data/software titles in any family. The value names
aren't confirmed against a live Canadian posting (there was only one), so
the title match is what's doing the work for now.
"""

from .base import NormalizedJob
from .smartrecruiters import scrape_smartrecruiters

JOB_FAMILY_GROUPS = {"Technology", "Data Science", "Data & Analytics", "Data Operations", "Engineering", "Product & Technology"}


def scrape() -> list[NormalizedJob]:
    return scrape_smartrecruiters(name="NielsenIQ", company="NielsenIQ", field_label="Job Family Group", field_values=JOB_FAMILY_GROUPS)
