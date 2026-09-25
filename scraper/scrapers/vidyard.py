"""Vidyard careers scraper, scoped to Canada + engineering / data / product departments.

vidyard.com/careers links to **Kula** (`careers.kula.ai/vidyard`), a
Next.js App Router page with no public JSON API. The job list is embedded
in the page's React Server Components payload, the
`self.__next_f.push([1, "<chunk>"])` script calls. Each chunk is a JSON
string literal; decoded and concatenated, they contain one
`"jobs":[{...}]` array, which is parsed with `raw_decode`. Plain GET, no
session. Investigated 2026-09-25: 2 jobs (sales/marketing), so this is
empty for now.

- Per job: `id` (stable numeric, external_id), `title`, `launch_at` (ISO
  datetime, posted date), `ats_job.ats_department.name`,
  `ats_job.offices[].{name,country}`. `listed` false = hidden.
- Job page: `careers.kula.ai/vidyard/<id>` (308-redirects to a slugged URL).
"""

import json
import logging
import re

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BOARD_URL = "https://careers.kula.ai/vidyard"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
FLIGHT_CHUNK_RE = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)')
JOBS_MARKER = '"jobs":['
DEPARTMENT_PATTERN = re.compile(r"engineer|product|data|technology|security|\bIT\b", re.IGNORECASE)


def scrape() -> list[NormalizedJob]:
    response = httpx.get(BOARD_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    flight = "".join(json.loads(chunk) for chunk in FLIGHT_CHUNK_RE.findall(response.text))
    start = flight.find(JOBS_MARKER)
    if start == -1:
        raise ValueError("Vidyard: no jobs array in Kula page payload — page structure changed?")
    raw_jobs, _ = json.JSONDecoder().raw_decode(flight, start + len(JOBS_MARKER) - 1)

    jobs = [
        _normalize(raw)
        for raw in raw_jobs
        if raw.get("listed", True) and DEPARTMENT_PATTERN.search(_department(raw)) and _is_canada(raw)
    ]
    logger.info("Vidyard: fetched %d matching jobs (of %d total)", len(jobs), len(raw_jobs))
    return jobs


def _department(raw: dict) -> str:
    return ((raw.get("ats_job") or {}).get("ats_department") or {}).get("name") or ""


def _offices(raw: dict) -> list[dict]:
    return (raw.get("ats_job") or {}).get("offices") or []


def _is_canada(raw: dict) -> bool:
    return any(office.get("country") == "Canada" for office in _offices(raw))


def _normalize(raw: dict) -> NormalizedJob:
    launched = raw.get("launch_at")
    return {
        "external_id": str(raw["id"]),
        "title": raw["title"].strip(),
        "url": f"{BOARD_URL}/{raw['id']}",
        "location": "; ".join(office["name"] for office in _offices(raw) if office.get("name")),
        "category": _department(raw),
        "posted_date": launched[:10] if launched else None,
        "platform": "Kula",
    }
