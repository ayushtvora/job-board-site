"""Optiver careers scraper (Canada / Technology and Quant Research jobs).

optiver.com/join-us/jobs/ is a custom site whose job list comes from its
own JSON endpoint, `GET https://www.optiver.com/en/api/v1/jobs` (found in
the page's embedded component config as `apiEndpoint`).

- `location=<office slug>` and `department=<slug>` are real server-side
  filters, and `page=N` pages through a filtered result (16 per page;
  `totalCount` in the response).
- Optiver has no Canadian office. The office list in the page's filter
  config (amsterdam, austin, chicago, hong-kong, london, mumbai, new-york,
  philadelphia, shanghai, singapore, sydney, taipei on 2026-10-02) is read
  on every run, and only offices matching CANADA_PATTERN are queried, so
  this returns nothing until a Canadian office appears.
- No job ID or posted date is exposed. `href` (e.g.
  `/join-us/jobs/technology/chicago/hpc-engineer/`) is stable per posting
  and used as external_id.
"""

import json
import logging

import httpx

from .base import CANADA_PATTERN, NormalizedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://www.optiver.com"
JOBS_PAGE = f"{BASE_URL}/join-us/jobs/"
API_URL = f"{BASE_URL}/en/api/v1/jobs"
DEPARTMENTS = ["technology", "quantitative-research-and-machine-learning"]
MAX_PAGES = 20
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"}
FILTER_GROUPS_MARKER = '"filterGroups":'


def scrape() -> list[NormalizedJob]:
    jobs: dict[str, NormalizedJob] = {}
    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        offices = _canadian_offices(client)
        for office in offices:
            for department in DEPARTMENTS:
                for page in range(1, MAX_PAGES + 1):
                    response = client.get(API_URL, params={"location": office, "department": department, "page": page})
                    response.raise_for_status()
                    items = response.json().get("items") or []
                    new = [i for i in items if i["href"] not in jobs]
                    for item in new:
                        jobs[item["href"]] = _normalize(item)
                    if not new:
                        break

    logger.info("Optiver: fetched %d jobs (Canadian offices: %s)", len(jobs), offices or "none")
    return list(jobs.values())


def _canadian_offices(client: httpx.Client) -> list[str]:
    response = client.get(JOBS_PAGE)
    response.raise_for_status()
    start = response.text.find(FILTER_GROUPS_MARKER)
    if start == -1:
        raise RuntimeError("Optiver jobs page no longer embeds its filter config")
    groups, _ = json.JSONDecoder().raw_decode(response.text, start + len(FILTER_GROUPS_MARKER))
    locations = next(g for g in groups if g["id"] == "location")["options"]
    return [o["value"] for o in locations if CANADA_PATTERN.search(o["label"])]


def _normalize(item: dict) -> NormalizedJob:
    return {
        "external_id": item["href"].strip("/").removeprefix("join-us/jobs/"),
        "title": item["title"].strip(),
        "url": f"{BASE_URL}{item['href']}",
        "location": item.get("location") or "",
        "category": item.get("domain") or "",
        "posted_date": None,
        "platform": "Optiver Careers (custom, in-house)",
    }
