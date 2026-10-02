"""Shared helper for SAP SuccessFactors "Jobs2Web" career-site scrapers.

Same page layer as Scotiabank (scrapers/scotiabank.py — see CLAUDE.md's
"BMO, CIBC, TD, Scotiabank scraping approach"): a category landing page at
`/go/<Label>/<id>/`, server-rendered HTML table (`tr.data-row`), paginated
by an offset *path segment* in steps of 25 (`/go/<Label>/<id>/25/`), sorted
newest-first with `sortColumn=referencedate&sortDirection=desc`.

Sites without category landing pages (e.g. Telus) use the generic
`/search/?q=` listing instead, paginated by a `startrow` query param
(same page size) — pass `category_path=None` for that mode, plus any
`search_params` the site's own search form sends (e.g. EY's
`optionsFacetsDD_country=CA`). `base_url` may include a path prefix (EY's
site lives under `careers.ey.com/ey`); job links are resolved against it.

Per row: title + `/job/<slug>/<numericId>/` link (numeric ID = external_id),
`.jobLocation` (multi-location rows end in "+N more…" — kept, minus the
ellipsis), `.jobDate` ("Sep 18, 2026"), and — on sites whose table has a
Department column — `.jobDepartment`, which `department_filter` can filter on.

Newer Jobs2Web templates (e.g. ATS Corporation) render each job as a
`li.job-tile` instead of a table row, with labeled `.section-field.<name>`
blocks (country, department, location, date) — parsed the same way. Those
pages say "Showing X to Y of N" instead of "Results X to Y of N"; past the
last page they keep re-serving it, so paging also stops once a page adds no
new job IDs.
"""

import logging
import re
from collections.abc import Callable
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .base import NormalizedJob

logger = logging.getLogger(__name__)

PAGE_SIZE = 25
MAX_PAGES = 50
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
JOB_ID_RE = re.compile(r"/(\d+)/?$")
RESULTS_COUNT_RE = re.compile(r"(?:Results|Showing) \d+ (?:to|&ndash;|–|-) \d+ of (\d+)")


def scrape_jobs2web(
    *,
    name: str,
    base_url: str,
    category_path: str | None,
    category_label: str,
    department_filter: Callable[[str], bool] | None = None,
    job_filter: Callable[[NormalizedJob], bool] | None = None,
    search_params: dict[str, str] | None = None,
) -> list[NormalizedJob]:
    """`category_path` like "/go/All-Jobs/9170201", or None for `/search/`
    (with optional extra `search_params`).
    If `department_filter` is given, only rows whose Department column it
    accepts are kept, and the department becomes the job's category.
    `job_filter` can drop parsed jobs client-side (e.g. by location)."""
    jobs: list[NormalizedJob] = []
    seen_ids: set[str] = set()
    offset = 0
    total: int | None = None

    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
        for _ in range(MAX_PAGES):
            params = {"q": "", "sortColumn": "referencedate", "sortDirection": "desc"}
            if category_path is None:
                url = f"{base_url}/search/"
                params |= {"locale": "en_US", "startrow": str(offset), **(search_params or {})}
            else:
                url = f"{base_url}{category_path}/{offset}/"
            response = client.get(url, params=params)
            response.raise_for_status()
            if total is None:
                match = RESULTS_COUNT_RE.search(response.text)
                total = int(match.group(1)) if match else 0

            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.select("tr.data-row") or soup.select("li.job-tile")
            if not rows:
                break
            new_on_page = 0
            for row in rows:
                job = _parse_row(row, base_url, category_label)
                if job is None or job["external_id"] in seen_ids:
                    continue
                seen_ids.add(job["external_id"])
                new_on_page += 1
                if department_filter is not None and not department_filter(job["category"]):
                    continue
                if job_filter is not None and not job_filter(job):
                    continue
                jobs.append(job)

            offset += PAGE_SIZE
            if (total and offset >= total) or new_on_page == 0:
                break
        else:
            logger.warning("%s scrape hit MAX_PAGES=%d without finishing — got %d jobs", name, MAX_PAGES, len(jobs))

    logger.info("%s: fetched %d jobs (site reported total=%s)", name, len(jobs), total)
    return jobs


def _parse_row(row, base_url: str, category_label: str) -> NormalizedJob | None:
    link = row.select_one("td.colTitle a.jobTitle-link") or row.select_one("a.jobTitle-link")
    if link is None:
        return None
    href = link["href"]
    match = JOB_ID_RE.search(href)
    if not match:
        return None
    location_el = row.select_one("td.colLocation .jobLocation") or row.select_one(".jobLocation") or _tile_field(row, "location")
    date_el = row.select_one("td.colDate .jobDate") or row.select_one(".jobDate") or _tile_field(row, "date")
    department_el = row.select_one(".jobDepartment") or row.select_one("td.colDepartment") or _tile_field(row, "department")
    location = location_el.get_text(" ", strip=True).rstrip("…").strip() if location_el else ""
    return {
        "external_id": match.group(1),
        "title": link.get_text(strip=True),
        "url": urljoin(f"{base_url}/", href),
        "location": location,
        "category": department_el.get_text(strip=True) if department_el else category_label,
        "posted_date": _parse_date(date_el.get_text(strip=True)) if date_el else None,
        "platform": "SuccessFactors",
    }


def _tile_field(tile, name: str):
    """Value element of a job tile's `.section-field.<name>` (desktop variant)."""
    field = tile.select_one(f".sub-section-desktop .section-field.{name}") or tile.select_one(f".section-field.{name}")
    return field.find("div") if field else None


def _parse_date(text: str) -> str | None:
    try:
        return datetime.strptime(text, "%b %d, %Y").date().isoformat()
    except ValueError:
        return None
