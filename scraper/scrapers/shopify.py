"""Shopify careers scraper, scoped to Canada/Americas + Engineering.

Shopify's real ATS is **Ashby** (every job links as
`shopify.com/careers?ashby_jid=<uuid>`), but there's no public Ashby job
board for it — Ashby's posting API 404s for every plausible org slug, and
Greenhouse/Lever 404 too. Instead, the careers page itself
(`shopify.com/careers`) is a React Router app whose loader data already
contains Shopify's full Ashby job export, and React Router serves that
loader data on its own at `shopify.com/careers.data` — no browser needed.

- `careers.data` is React Router's "turbo-stream" encoding, not plain JSON:
  one JSON array where objects are `{"_<keyIndex>": <valueIndex>}` and
  arrays are lists of value indices, all pointing back into that same flat
  array (for deduplication). `_decode_turbo_stream` below flattens it back
  into normal JSON. Negative indices are sentinels (undefined/null/etc).
- Jobs are at `["($locale)/careers"]["data"]["jobPostingsWithJobs"]`, each
  `{"jobPosting": {...}, "job": {...}}`. `jobPosting` has `id` (stable UUID,
  used as `external_id`), `title`, `teamName` (e.g. "Engineering"),
  `publishedDate` (plain ISO date), `externalLink`, and `locationIds`
  (primary + secondary Ashby location UUIDs).
- Location UUIDs resolve via the sibling `atsLocations` list, each with a
  `name` and (usually) `address.postalAddress.addressCountry`.
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

DATA_URL = "https://www.shopify.com/careers.data"
ROUTE_KEY = "($locale)/careers"
TEAM_NAME = "Engineering"
MATCHING_COUNTRIES = {"canada", "americas"}

# Negative indices in turbo-stream encode values JSON can't reference by index.
_TURBO_SENTINELS = {-1: None, -2: None, -3: None, -4: None, -5: None, -6: None, -7: None}


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as client:
        response = client.get(DATA_URL)
        response.raise_for_status()
        first_line = response.text.split("\n", 1)[0]

    data = _decode_turbo_stream(first_line)[ROUTE_KEY]["data"]
    locations = {loc["id"]: loc for loc in data["atsLocations"]}
    postings = [entry["jobPosting"] for entry in data["jobPostingsWithJobs"]]

    jobs = [
        _normalize(posting, locations)
        for posting in postings
        if posting.get("teamName") == TEAM_NAME and _matches_location(posting, locations)
    ]
    logger.info("Shopify: fetched %d matching jobs (of %d total postings)", len(jobs), len(postings))
    return jobs


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
