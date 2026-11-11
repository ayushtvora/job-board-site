"""Mars, Incorporated careers scraper, scoped to Canada + Digital Technologies / Data jobs.

careers.mars.com is a Phenom front-end (983 postings worldwide on
2026-11-11) whose apply links all go to Workday, tenant
`mars.wd3.myworkdayjobs.com/External`, so this reads that tenant through
the shared helper in scrapers/workday_cxs.py.

- Category facet `jobFamilyGroup`: "Digital Technologies"
  (`f7694590cd500154005589ee200d5b0b`) and "Data, Analytics & Insights"
  (`f7694590cd500194a30483ee200d590b`).
- **No country facet**, only per-city `locations` (named "CAN-<Province>-
  <City>", plus one "CA - Quebec – Trois-Rivieres"), so every Canadian one
  is passed (same approach as Cisco and Mastercard). A new Canadian site
  won't be picked up until its ID is added here. Locations are rewritten
  to "<City>, <Province>, Canada" so base.job_cities finds the city.
- On 2026-11-11 Mars had 36 Canadian postings (mostly sales, supply and
  plant roles around Bolton and Guelph) and **0** in the two tech groups.
  So this is expected to be empty or nearly so, apart from whatever the
  helper's keyword searches find.
"""

import re

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CATEGORY_FACET_IDS = [
    "f7694590cd500154005589ee200d5b0b",  # Digital Technologies
    "f7694590cd500194a30483ee200d590b",  # Data, Analytics & Insights
]
CANADA_LOCATION_IDS = [
    "bffb012ba4fb1000fe57cf1ff4ed0000",  # CAN-Alberta-Acheson
    "f7694590cd500160e5303843b00d298f",  # CAN-Alberta-Calgary
    "f7694590cd5001f960f43143b00d1a8f",  # CAN-Alberta-Edmonton
    "f7694590cd5001d069928243b00dce8f",  # CAN-British Columbia-Vancouver
    "6c26454652a81000fc6a487469b10000",  # CAN-British Columbia-Vernon
    "f7694590cd5001a2751f7643b00db08f",  # CAN-Ontario-Bolton
    "f7694590cd500153af377243b00da68f",  # CAN-Ontario-Guelph
    "f7694590cd500171c25a7043b00da18f",  # CAN-Ontario-Kingston
    "f7694590cd5001165e886c43b00d978f",  # CAN-Ontario-London - Tillsonburg
    "f7694590cd5001a894a37843b00db58f",  # CAN-Ontario-Newmarket
    "2656a67c0fd11001de03980509d70000",  # CAN-Ontario-Sudbury
    "f7694590cd500176361b7443b00dab8f",  # CAN-Ontario-Toronto
    "f7694590cd5001b5d6445543b00d608f",  # CAN-Quebec-Montreal
    "f7694590cd5001a713d75043b00d568f",  # CAN-Quebec-Quebec City
    "f7694590cd5001e7c56c9443b00df68f",  # CAN-Saskatchewan-Regina
    "ca6ebafed88610015f848ee202d20000",  # CA - Quebec - Trois-Rivieres
]


# "CAN-Ontario-Bolton" / "CA - Quebec – Trois-Rivieres": the city comes after
# the province, which base.job_cities only reads the other way round.
LOCATION_PATTERN = re.compile(r"\bCAN?\s*-\s*([A-Za-z ]+?)\s*[-–]\s*([^;(]+?)(?=\s*(?:;|\(|$))")


def scrape() -> list[NormalizedJob]:
    jobs = scrape_workday(
        name="Mars",
        base_url="https://mars.wd3.myworkdayjobs.com",
        tenant="mars",
        site="External",
        applied_facets={
            "jobFamilyGroup": CATEGORY_FACET_IDS,
            "locations": CANADA_LOCATION_IDS,
        },
        category_label="Digital Technologies",
    )
    return [{**job, "location": _readable_location(job["location"])} for job in jobs]


def _readable_location(location: str) -> str:
    """"CAN-Ontario-Bolton" -> "Bolton, Ontario, Canada"."""
    return LOCATION_PATTERN.sub(lambda m: f"{m.group(2)}, {m.group(1)}, Canada", location)
