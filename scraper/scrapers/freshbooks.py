"""FreshBooks careers scraper, scoped to Canada + engineering / data / IT departments.

FreshBooks' job board is hosted by **Gem** (`jobs.gem.com/freshbooks`).
Gem's public job-board API returns every posting in one unauthenticated
call: `GET https://api.gem.com/job_board/v0/freshbooks/job_posts/`. It's
shaped like Greenhouse's Board API (`departments[]`, `offices[]`,
`location.name`, `first_published_at`, `absolute_url`). Investigated
2026-09-25: only 2 postings (finance, brand design), so this is empty for
now.

- Canada is matched on `location.name` and office names/locations, like
  the Greenhouse helper. FreshBooks lists a dozen Canadian offices
  ("Toronto", "Canada - Remote", ...).
- `id` is Gem's opaque stable posting ID, used as external_id
  (`requisition_id` is also set, but not on every board).
"""

import logging
import re

import httpx

from .base import CANADA_PATTERN, NormalizedJob, is_core_title

logger = logging.getLogger(__name__)

API_URL = "https://api.gem.com/job_board/v0/freshbooks/job_posts/"
DEPARTMENT_PATTERN = re.compile(r"engineer|develop|data|technology|security|\bIT\b|platform|product", re.IGNORECASE)


def scrape() -> list[NormalizedJob]:
    response = httpx.get(API_URL, timeout=30)
    response.raise_for_status()
    posts = response.json()
    jobs = [
        _normalize(post)
        for post in posts
        if (DEPARTMENT_PATTERN.search(_departments(post)) or is_core_title(post["title"]))
        and any(CANADA_PATTERN.search(s) for s in _locations(post))
    ]
    logger.info("FreshBooks: fetched %d matching jobs (of %d total)", len(jobs), len(posts))
    return jobs


def _departments(post: dict) -> str:
    return ", ".join(d["name"].strip() for d in post.get("departments") or [])


def _locations(post: dict) -> list[str]:
    strings = [(post.get("location") or {}).get("name") or ""]
    for office in post.get("offices") or []:
        strings.append(office.get("name") or "")
        strings.append((office.get("location") or {}).get("name") or "")
    return [s for s in strings if s]


def _normalize(post: dict) -> NormalizedJob:
    published = post.get("first_published_at")
    canadian = [s for s in dict.fromkeys(_locations(post)) if CANADA_PATTERN.search(s)]
    return {
        "external_id": post["id"],
        "title": post["title"].strip(),
        "url": post["absolute_url"],
        "location": "; ".join(canadian),
        "category": _departments(post),
        "posted_date": published[:10] if published else None,
        "platform": "Gem",
    }
