"""Fetch job descriptions for jobs saved without one.

Most scrapers read a listing that has no description, so after every
company's jobs are saved, `fetch_missing_descriptions` fetches each new
job's description once, from its own page or API. A job that already has
one is never fetched again. A job whose fetch fails is retried on the next
run, up to MAX_ATTEMPTS times, and then left without one (the web app then
scores it on its title alone).

Fetchers are picked by the job's URL (`FETCHERS`), falling back to
`fetch_generic`, which reads the page's schema.org JobPosting JSON-LD (most
career sites publish it for Google Jobs) or else its main text block. A
fetcher returns plain text (via `base.clean_description`) or None when the
page has no usable description.

This never fails a scrape run or writes scrape_runs: every job's failure is
caught and only counted in description_attempts.
"""

import json
import logging
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import httpx
from bs4 import BeautifulSoup

from scrapers.base import clean_description

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
WORKERS = 16
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36",
    "Accept-Language": "en-CA,en;q=0.9",
}
# Platforms whose pages need a real browser (see CLAUDE.md); their jobs
# are scored on their title rather than holding the browser lock for
# hundreds of page loads.
SKIP_PLATFORMS = {"Meta Careers (custom, in-house)", "Uber Careers (custom, in-house)"}


def fetch_missing_descriptions(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, url, platform FROM jobs
            WHERE is_active AND description IS NULL AND description_attempts < %s
              AND url <> '' AND NOT (platform = ANY(%s))
            ORDER BY first_seen_at DESC
            """,
            (MAX_ATTEMPTS, list(SKIP_PLATFORMS)),
        )
        rows = cur.fetchall()
    if not rows:
        return
    logger.info("Fetching descriptions for %d jobs", len(rows))

    with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:

        def fetch(row: tuple) -> tuple[int, str | None]:
            job_id, url, _platform = row
            try:
                return job_id, fetch_description(client, url)
            except Exception as exc:
                logger.debug("description fetch failed for job %s (%s): %s", job_id, url, exc)
                return job_id, None

        with ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="describe") as pool:
            results = list(pool.map(fetch, rows))

    found = 0
    with conn.cursor() as cur:
        for job_id, description in results:
            if description:
                found += 1
                cur.execute("UPDATE jobs SET description = %s WHERE id = %s", (description, job_id))
            else:
                cur.execute(
                    "UPDATE jobs SET description_attempts = description_attempts + 1 WHERE id = %s", (job_id,)
                )
    conn.commit()
    logger.info("Fetched %d of %d descriptions", found, len(rows))


def fetch_description(client: httpx.Client, url: str) -> str | None:
    for pattern, fetcher in FETCHERS:
        match = pattern.search(url)
        if match:
            return fetcher(client, url, match)
    return fetch_generic(client, url)


def fetch_workday(client: httpx.Client, url: str, match: re.Match) -> str | None:
    """A myworkdayjobs.com job page's CXS detail endpoint (see
    scrapers/workday_cxs.py). Covers the Phenom sites (RBC, BMO, Adobe,
    ...) whose job links go to Workday."""
    host, tenant, site, path = match.group("host", "tenant", "site", "path")
    response = client.get(f"https://{host}/wday/cxs/{tenant}/{site}/job/{path}")
    response.raise_for_status()
    return clean_description(response.json()["jobPostingInfo"].get("jobDescription"))


def fetch_oracle(client: httpx.Client, url: str, match: re.Match) -> str | None:
    """Oracle Recruiting Cloud's public requisition-details REST resource
    (same host as the job page; see scrapers/oracle_recruiting.py)."""
    host, site, job_id = match.group("host", "site", "id")
    response = client.get(
        f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails",
        params={"expand": "all", "onlyData": "true", "finder": f'ById;Id="{job_id}",siteNumber={site}'},
    )
    response.raise_for_status()
    items = response.json().get("items") or []
    if not items:
        return None
    item = items[0]
    return clean_description(
        "".join(
            item.get(key) or ""
            for key in ("ExternalDescriptionStr", "ExternalResponsibilitiesStr", "ExternalQualificationsStr")
        )
    )


def fetch_apple(client: httpx.Client, url: str, match: re.Match) -> str | None:
    """jobs.apple.com job pages embed the posting in the same
    `__staticRouterHydrationData` blob as the search page (see
    scrapers/apple.py), as a JSON.parse("...") string literal."""
    response = client.get(url)
    response.raise_for_status()
    text = response.text
    start = text.find("JSON.parse(", text.find("__staticRouterHydrationData"))
    if start == -1:
        return None
    literal, _ = json.JSONDecoder().raw_decode(text, start + len("JSON.parse("))
    job = (json.loads(literal).get("loaderData", {}).get("jobDetails") or {}).get("jobsData") or {}
    sections = [
        ("", job.get("jobSummary")),
        ("Description", job.get("description")),
        ("Minimum Qualifications", job.get("minimumQualifications")),
        ("Preferred Qualifications", job.get("preferredQualifications")),
    ]
    return clean_description("\n\n".join(f"{title}\n{body}".strip() for title, body in sections if body))


def fetch_gcjobs(client: httpx.Client, url: str, match: re.Match) -> str | None:
    """Most GC Jobs postings (e.g. NRC's, StatCan's) are only a "You will
    leave the GC Jobs Web site" page linking to the hiring organization's
    own posting, so that link is followed."""
    response = client.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    if "You will leave the GC Jobs" not in soup.get_text(" "):
        return description_from_page(soup)
    main = soup.find("main") or soup
    for link in main.find_all("a", href=True):
        href = link["href"]
        if href.startswith("http") and "cfp-psc.gc.ca" not in href:
            return fetch_generic(client, href)
    return None


FETCHERS: list[tuple[re.Pattern, Callable[[httpx.Client, str, re.Match], str | None]]] = [
    (re.compile(r"https?://emploisfp-psjobs\.cfp-psc\.gc\.ca/"), fetch_gcjobs),
    (
        re.compile(
            r"https?://(?P<host>(?P<tenant>[\w-]+)\.wd\d+\.myworkdayjobs\.com)"
            # Phenom sites' apply links end in "/apply", which isn't part
            # of the posting's path.
            r"(?:/[a-z]{2}-[A-Z]{2})?/(?P<site>[\w-]+)/job/(?P<path>[^?#]+?)(?:/apply)?/?(?:[?#]|$)"
        ),
        fetch_workday,
    ),
    (
        re.compile(
            r"https?://(?P<host>[\w.-]+\.oraclecloud\.com)/hcmUI/CandidateExperience/[\w-]+/sites/(?P<site>[\w-]+)/job/(?P<id>\d+)"
        ),
        fetch_oracle,
    ),
    (re.compile(r"https?://jobs\.apple\.com/[\w-]+/details/"), fetch_apple),
]


def fetch_generic(client: httpx.Client, url: str) -> str | None:
    response = client.get(url)
    response.raise_for_status()
    text = response.text
    soup = BeautifulSoup(text, "html.parser")
    return (
        description_from_json_ld(soup)
        or description_from_phenom(text)
        or description_from_embedded_json(text)
        or description_from_page(soup)
    )


def description_from_phenom(text: str) -> str | None:
    """Phenom job pages (Bell, OpenText, ...) embed the posting in the same
    `phApp.ddo` blob as their search pages (see scrapers/phenom.py), under
    jobDetail.data.job."""
    marker = "phApp.ddo = "
    start = text.find(marker)
    if start == -1:
        return None
    try:
        ddo, _ = json.JSONDecoder().raw_decode(text, start + len(marker))
    except ValueError:
        return None
    job = ((ddo.get("jobDetail") or {}).get("data") or {}).get("job") or {}
    return clean_description(job.get("description"))


def description_from_embedded_json(text: str) -> str | None:
    """A `"jobDescription": "..."` JSON string anywhere in the page, as in
    the Next.js payloads of Dayforce job pages."""
    for match in re.finditer(r'"jobDescription"\s*:\s*(?=")', text):
        try:
            value, _ = json.JSONDecoder().raw_decode(text, match.end())
        except ValueError:
            continue
        description = clean_description(value)
        if description:
            return description
    return None


def description_from_json_ld(soup: BeautifulSoup) -> str | None:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "", strict=False)
        except ValueError:
            continue
        for item in _json_ld_items(data):
            if item.get("@type") == "JobPosting" and item.get("description"):
                return clean_description(item["description"])
    return None


def _json_ld_items(data) -> list[dict]:
    if isinstance(data, list):
        return [item for entry in data for item in _json_ld_items(entry)]
    if isinstance(data, dict):
        return [data, *_json_ld_items(data.get("@graph") or [])]
    return []


# Elements that usually hold the posting itself, most specific first.
_DESCRIPTION_SELECTORS = [
    "[class*='job-description' i]",
    "[id*='job-description' i]",
    "[class*='jobdescription' i]",
    "[id*='jobdescription' i]",
    "[class*='description' i]",
    "[id*='description' i]",
    "article",
    "main",
]
# Text this short is a page shell (a JS app's loading screen, an error
# page), not a posting.
_MIN_PAGE_TEXT = 400


def description_from_page(soup: BeautifulSoup) -> str | None:
    """The largest element matching the first selector that finds a real
    block of text."""
    # Not <form>: some sites (SAP's classic SuccessFactors pages, BC Public
    # Service) wrap the whole page in one.
    for tag in soup(["script", "style", "noscript", "nav", "footer"]):
        tag.decompose()
    for selector in _DESCRIPTION_SELECTORS:
        candidates = soup.select(selector)
        if not candidates:
            continue
        best = max(candidates, key=lambda el: len(el.get_text(" ", strip=True)))
        if len(best.get_text(" ", strip=True)) >= _MIN_PAGE_TEXT:
            return clean_description(str(best))
    return None
