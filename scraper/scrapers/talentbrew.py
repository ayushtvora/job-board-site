"""Shared helper for Radancy TalentBrew career-site scrapers (Intuit, Synopsys).

TalentBrew sites (`/search-jobs`, assets from tbcdn.talentbrew.com) render
results client-side from an XHR endpoint that works with plain HTTP:

    GET <base_url>/search-jobs/results?OrganizationIds=<org>&CurrentPage=N&RecordsPerPage=50
        &SearchType=5&SearchResultsModuleName=Search Results
        &FacetFilters[i].ID=<id>&FacetFilters[i].FacetType=<type>&FacetFilters[i].IsApplied=true

It returns JSON whose `results` value is an HTML fragment (`section#search-results`,
with `data-total-pages`) and `filters` holds the facet list. Facet types:
1 = category, 2 = country (the ID is the GeoNames ID; Canada = 6251999).
Category IDs come from `input[data-facet-type="1"]` in `filters`. The org
ID is in the site's own job URLs (`/job/<city>/<slug>/<org>/<id>`).

- Each result is an `a[href*="/job/"]` whose trailing number is TalentBrew's
  own stable job ID, used as `external_id`.
- Tenants style results differently: Synopsys shows `.category` and
  `.job-date-posted` ("MM/DD/YYYY"); Intuit shows neither, so its category
  comes from the item's `data-category`, or else the passed label, and
  `posted_date` is None.
- Data roles come from a second search with only the Canada facet and
  `Keywords=<term>` for each of `CORE_SEARCH_TERMS`, keeping core titles (data, ML, software).
- TalentBrew is only the career-site layer; the apply flow goes to the real
  ATS (Avature for both Intuit and Synopsys), passed as `platform`.
"""

import logging
import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from .base import CORE_SEARCH_TERMS, NormalizedJob, is_core_title

logger = logging.getLogger(__name__)

CANADA_GEONAME_ID = "6251999"
KEYWORD_SEARCH_CATEGORY = "Keyword search"
MAX_PAGES = 20
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
}
JOB_ID_RE = re.compile(r"/(\d+)/?$")


def scrape_talentbrew(
    *,
    name: str,
    base_url: str,
    org_id: str,
    category_ids: list[str],
    category_label: str,
    platform: str,
) -> list[NormalizedJob]:
    """Scrape Canada + the given category facet IDs, then Canada + a keyword
    search for data roles."""
    jobs: dict[str, NormalizedJob] = {}

    with httpx.Client(timeout=30, headers=HEADERS) as client:

        def scrape_pass(facets: list[tuple[str, str]], keywords: str, label: str, data_only: bool) -> None:
            total_pages = 1
            page = 1
            while page <= min(total_pages, MAX_PAGES):
                params = {
                    "OrganizationIds": org_id,
                    "CurrentPage": str(page),
                    "RecordsPerPage": "50",
                    "SearchType": "5",
                    "SearchResultsModuleName": "Search Results",
                    "SearchFiltersModuleName": "Search Filters",
                }
                if keywords:
                    params["Keywords"] = keywords
                for i, (facet_id, facet_type) in enumerate(facets):
                    params[f"FacetFilters[{i}].ID"] = facet_id
                    params[f"FacetFilters[{i}].FacetType"] = facet_type
                    params[f"FacetFilters[{i}].IsApplied"] = "true"
                response = client.get(f"{base_url}/search-jobs/results", params=params)
                response.raise_for_status()
                soup = BeautifulSoup(response.json()["results"], "html.parser")
                section = soup.select_one("section#search-results")
                if section is not None and section.get("data-total-pages"):
                    total_pages = int(section["data-total-pages"])

                new_on_page = 0
                data_on_page = False
                for link in soup.select("#search-results-list a[href*='/job/']"):
                    job = _parse(link, base_url, label, platform)
                    if job is None:
                        continue
                    data_on_page = data_on_page or is_core_title(job["title"])
                    if job["external_id"] in jobs or (data_only and not is_core_title(job["title"])):
                        continue
                    jobs[job["external_id"]] = job
                    new_on_page += 1
                if (new_on_page == 0 and not data_only) or (data_only and not data_on_page):
                    break
                page += 1

        canada = [(CANADA_GEONAME_ID, "2")]
        scrape_pass(canada + [(category_id, "1") for category_id in category_ids], "", category_label, data_only=False)
        for term in CORE_SEARCH_TERMS:
            scrape_pass(canada, term, KEYWORD_SEARCH_CATEGORY, data_only=True)

    logger.info("%s: fetched %d jobs", name, len(jobs))
    return list(jobs.values())


def _parse(link, base_url: str, category_label: str, platform: str) -> NormalizedJob | None:
    href = link["href"]
    match = JOB_ID_RE.search(href)
    if not match:
        return None
    title_el = link.select_one("h2") or link
    location_el = link.select_one(".job-location")
    category_el = link.select_one(".category")
    date_el = link.select_one(".job-date-posted")
    item = link.find_parent("li")
    category = (
        _strip_label(category_el.get_text(" ", strip=True)) if category_el else (item.get("data-category") if item else None)
    )
    return {
        "external_id": match.group(1),
        "title": title_el.get_text(" ", strip=True),
        "url": href if href.startswith("http") else f"{base_url}{href}",
        "location": location_el.get_text(" ", strip=True) if location_el else "",
        "category": category or category_label,
        "posted_date": _parse_date(_strip_label(date_el.get_text(" ", strip=True))) if date_el else None,
        "platform": platform,
    }


def _strip_label(text: str) -> str:
    """"Category: Engineering" -> "Engineering"."""
    return text.split(":", 1)[1].strip() if ":" in text else text


def _parse_date(text: str) -> str | None:
    try:
        return datetime.strptime(text, "%m/%d/%Y").date().isoformat()
    except ValueError:
        return None
