"""Shopify careers scraper, scoped to Canada/Americas + Engineering.

Shopify's real ATS is **Ashby** (every job links as
`shopify.com/careers?ashby_jid=<uuid>`), but there's no public Ashby job
board for it — Ashby's posting API 404s for every plausible org slug, and
Greenhouse/Lever 404 too. Instead, the careers site is a React Router app,
and React Router serves each page's loader data on its own at
`<page>.data` — no browser needed.

- `careers.data` is React Router's "turbo-stream" encoding, not plain JSON:
  one JSON array where objects are `{"_<keyIndex>": <valueIndex>}` and
  arrays are lists of value indices, all pointing back into that same flat
  array (for deduplication). `_decode_turbo_stream` below flattens it back
  into normal JSON. Negative indices are sentinels (undefined/null/etc).
- The job list is `/careers/jobs.data`, at
  `["($locale)/careers/jobs"]["data"]["roles"]`: `id` (the Ashby posting
  UUID, used as `external_id`), `title`, `disciplineSlug` and `href`, but
  no posted date. (Until 2026-10 `/careers.data` itself carried the full
  Ashby export as `jobPostingsWithJobs` + `atsLocations`; both are gone.)
- So each "engineering-data" role's own page, `<href>.data`, is fetched
  for its `jobPosting` (`teamName` e.g. "Engineering", `publishedDate`
  plain ISO date, `externalLink`, `locationIds`) and its `locations`
  (each with a `name` and, usually, `address.postalAddress.addressCountry`).
  The "Engineering & Data" discipline also has data roles, so scope is
  still `teamName == "Engineering"`.
- **Canada caveat**: Shopify is remote-first. As of 2026-09-25 all 44
  Engineering postings are listed only under the region "Americas" (country
  field literally "Americas"), not a Canadian city — same shape of problem
  as Canonical's "Home Based - Americas". A strict Canada-only filter would
  return 0, so this scraper keeps jobs whose locations include either a
  Canadian location *or* the "Americas" region.
"""

import json
import logging

import httpx

from .base import NormalizedJob

logger = logging.getLogger(__name__)

BASE_URL = "https://www.shopify.com"
LIST_ROUTE_KEY = "($locale)/careers/jobs"
DETAIL_ROUTE_KEY = "($locale)/careers/$posting"
DISCIPLINE_SLUG = "engineering-data"
TEAM_NAME = "Engineering"
MATCHING_COUNTRIES = {"canada", "americas"}

# Negative indices in turbo-stream encode values JSON can't reference by index.
_TURBO_SENTINELS = {-1: None, -2: None, -3: None, -4: None, -5: None, -6: None, -7: None}


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as client:
        roles = _load(client, "/careers/jobs", LIST_ROUTE_KEY)["roles"]
        candidates = [role for role in roles if role.get("disciplineSlug") == DISCIPLINE_SLUG]

        jobs = []
        for role in candidates:
            detail = _load(client, role["href"], DETAIL_ROUTE_KEY)
            posting = detail["jobPosting"]
            locations = {loc["id"]: loc for loc in detail.get("locations") or []}
            if posting.get("teamName") == TEAM_NAME and _matches_location(posting, locations):
                jobs.append(_normalize(posting, locations))

    logger.info(
        "Shopify: fetched %d matching jobs (of %d %s roles, %d total)",
        len(jobs), len(candidates), DISCIPLINE_SLUG, len(roles),
    )
    return jobs


def _load(client: httpx.Client, path: str, route_key: str) -> dict:
    """Fetch a page's React Router loader data."""
    response = client.get(f"{BASE_URL}{path}.data")
    response.raise_for_status()
    first_line = response.text.split("\n", 1)[0]
    return _decode_turbo_stream(first_line)[route_key]["data"]


def _decode_turbo_stream(line: str) -> dict:
    values = json.loads(line)
    memo: dict[int, object] = {}

    def hydrate(index: int):
        if index < 0:
            return _TURBO_SENTINELS.get(index)
        if index in memo:
            return memo[index]
        value = values[index]
        if isinstance(value, dict):
            out: dict = {}
            memo[index] = out
            for key, value_index in value.items():
                out[values[int(key[1:])]] = hydrate(value_index)
            return out
        if isinstance(value, list):
            # A list starting with a string is a typed special value (e.g.
            # ["D", <timestamp>] for a Date) rather than an array of indices.
            if value and isinstance(value[0], str):
                return value[1] if len(value) > 1 else None
            out_list: list = []
            memo[index] = out_list
            out_list.extend(hydrate(i) for i in value)
            return out_list
        return value

    return hydrate(0)


def _location_ids(posting: dict) -> list[str]:
    ids = posting.get("locationIds") or {}
    return [ids.get("primaryLocationId"), *(ids.get("secondaryLocationIds") or [])]


def _country(location: dict) -> str:
    address = (location.get("address") or {}).get("postalAddress") or {}
    return (address.get("addressCountry") or location.get("name") or "").strip().lower()


def _matches_location(posting: dict, locations: dict) -> bool:
    return any(
        _country(locations[loc_id]) in MATCHING_COUNTRIES
        for loc_id in _location_ids(posting)
        if loc_id in locations
    )


def _normalize(posting: dict, locations: dict) -> NormalizedJob:
    names = [
        locations[loc_id]["name"].strip()
        for loc_id in _location_ids(posting)
        if loc_id in locations
    ]
    workplace = posting.get("workplaceType")
    location = ", ".join(names)
    if workplace:
        location = f"{location} ({workplace})"
    return {
        "external_id": posting["id"],
        "title": posting["title"],
        "url": posting.get("externalLink") or f"https://www.shopify.com/careers?ashby_jid={posting['id']}",
        "location": location,
        "category": posting.get("teamName") or "",
        "posted_date": posting.get("publishedDate"),
        "platform": "Ashby",
    }
