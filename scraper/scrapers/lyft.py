"""Lyft careers scraper, scoped to Canada + technology orgs.

Greenhouse (board token `lyft`), via the shared helper in
scrapers/greenhouse.py. Investigated 2026-09-25: 177 jobs, 73 in Canada
(Toronto, Montréal).

Lyft's tree is organised by business area under an "All Talent Team Access"
root rather than by discipline. So the product/engineering areas are listed
("Foundations & AI Transformation", "Rider", "Driver, Supply & PII", ...),
plus the tech sub-teams of non-tech areas ("SCC Tech", "Global Growth
Tech"). "LUS" is Lyft Urban Solutions (bikes/scooters), which includes
hardware engineering. "Early Talent" (interns) is included.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

DEPARTMENTS = {
    "Foundations & AI Transformation",
    "Rider",
    "Driver, Supply & PII",
    "Marketplace",
    "LUS",
    "SCC Tech",
    "SCC Analytics",
    "Global Growth Tech",
    "Early Talent",
}
EXCLUDE = {"Rider Leadership"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="Lyft", board_token="lyft", departments=DEPARTMENTS, exclude_departments=EXCLUDE)
