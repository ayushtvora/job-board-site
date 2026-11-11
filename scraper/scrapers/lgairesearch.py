"""LG AI Research careers scraper (Canada, all departments).

Greenhouse, board token `lgairesearch`, via scrapers/greenhouse.py. LG AI
Research runs a Toronto lab. Investigated 2026-11-10: 37 postings, none in
Canada (Seoul and Ann Arbor), a legitimate empty result. Every posting is
a research/engineering role, so there's no department filter.
"""

from .base import NormalizedJob
from .greenhouse import scrape_greenhouse


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(name="LG AI Research", board_token="lgairesearch", departments=None)
