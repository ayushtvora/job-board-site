"""General Motors careers scraper (Canada / software and engineering job families).

Workday CXS, tenant `generalmotors.wd5.myworkdayjobs.com/Careers_GM`
(search.jobs.gm.com is a front-end over it), via scrapers/workday_cxs.py.

- Country facet `Location_Country`, Canada = the shared
  `a30a87ed25634629aa6c3958aa2b91ea` (46 jobs on 2026-10-02, mostly the
  Markham/Oshawa tech centres).
- `jobFamilyGroup` "Engineering Group" also holds facilities and industrial
  engineers, so scope uses the finer `jobFamily` facet instead: the
  software, data, AI/ML, cyber, cloud and vehicle-systems families below
  (31 of the 46 Canadian postings were "Software Engineering", including
  co-op students).
"""

from .base import NormalizedJob
from .workday_cxs import scrape_workday

CANADA_FACET_ID = "a30a87ed25634629aa6c3958aa2b91ea"
JOB_FAMILY_IDS = [
    "81219c9120850116c34e56729c1b88a0",  # Software Engineering
    "81219c912085016a2ee374729c1b17a1",  # Software Development
    "81219c91208501c7f1f87b729c1b3ba1",  # Software Test Engineering
    "51884505018d1001e72ac80395d50000",  # Software Engineering - SRE
    "89f07280276d10015a37affdd09c0000",  # Cloud Engineering
    "81219c912085018437336c729c1bdca0",  # Data Engineering
    "81219c91208501dac15453729c1b76a0",  # Data Science
    "6813d8bd0ee501f7cc26287a90269db8",  # Artificial Intelligence Machine Learning Scientist
    "9a7db3783a6501542c31d6869026e187",  # Machine Learning Engineering
    "81219c91208501e95b8a81729c1b5da1",  # Cyber Security
    "81219c91208501303e0782729c1b5fa1",  # Architecture Engineering
    "51884505018d1001e73172cdbbcb0000",  # Systems Engineering
    "51884505018d1001e73909ec18060000",  # Vehicle Systems Engineering
    "adcf1fd4b0811001e749ea9f631c0000",  # Hardware Engineering
    "81219c9120850185bacd66729c1bb6a0",  # Controls System Engineering
]


def scrape() -> list[NormalizedJob]:
    return scrape_workday(
        name="General Motors",
        base_url="https://generalmotors.wd5.myworkdayjobs.com",
        tenant="generalmotors",
        site="Careers_GM",
        applied_facets={"Location_Country": [CANADA_FACET_ID], "jobFamily": JOB_FAMILY_IDS},
        category_label="Software / Engineering",
    )
