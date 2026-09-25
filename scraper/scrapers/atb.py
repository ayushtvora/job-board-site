"""ATB Financial careers scraper, scoped to Technology / Data, AI & Analytics.

`careers.atb.com` is **Eightfold**, same `pcsx` search API as
Microsoft/Autodesk, via the shared helper in scrapers/eightfold.py. ATB is
Alberta-only, and `location=Canada` returns everything (43 jobs,
2026-09-25). Most are retail banking; the tech departments are
"Technology" and "Data, AI & Analytics".
"""

from .base import NormalizedJob
from .eightfold import scrape_eightfold

DEPARTMENTS = {"Technology", "Data, AI & Analytics"}


def scrape() -> list[NormalizedJob]:
    return scrape_eightfold(
        name="ATB Financial",
        base_url="https://careers.atb.com",
        domain="atb.com",
        job_filter=lambda raw: (raw.get("department") or "") in DEPARTMENTS,
    )
