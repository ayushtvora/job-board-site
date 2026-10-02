"""PlayStation / Sony Interactive Entertainment careers scraper (Canada /
engineering titles).

careers.playstation.com lists jobs from several Greenhouse boards. The main
one, `sonyinteractiveentertainmentglobal`, has all the Canadian postings
(Waterloo, Montreal, remote; 17 of 207 on 2026-10-02). The studio boards
(`siei`, `pdi`, `naughtydog`, `insomniac`, `housemarque`, `firesprite`,
`teamlfg`) had none, and `haven`/`havenenglish` only repeat Haven Studios'
Montreal postings that are already on the main board.

This is separate from the Sony scraper (scrapers/sony.py), which reads Sony
Group's own Workday tenant.

Departments here are cost centres ("Admin (PE)", "FSEE US"), not
disciplines, so scope is a title match on engineering/developer/data roles.
"""

import re

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse

TITLE_PATTERN = re.compile(
    r"engineer|developer|sdet|software|programmer|data|devops|\bsre\b|security|technical|machine learning|\bai\b",
    re.IGNORECASE,
)


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(
        name="PlayStation",
        board_token="sonyinteractiveentertainmentglobal",
        departments=None,
        job_filter=lambda raw: bool(TITLE_PATTERN.search(raw["title"])),
    )
