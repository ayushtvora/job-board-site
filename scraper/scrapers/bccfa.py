"""BC Centre for Ability careers scraper (tech roles).

bc-cfa.org/about-us/careers links each posting to ADP Workforce Now's
career centre (client `cid=1e20e2eb-738c-4c13-b495-ca09f4326217`). Its
public JSON feed needs no auth:
`GET https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions?cid=<cid>&ccId=19000101_000001&lang=en_CA&$top=100`.

- 6 postings on 2026-10-02, all in BC (Burnaby, Vancouver, North Shore,
  WorkBC offices) and all clinical or social work. The only category-like
  field is "JOB CLASS" (Clinician, Staff, Leadership), so scope is a tech
  title match, and an empty result is expected most of the time.
- Per requisition: `itemID` (stable, used for the apply link),
  `requisitionTitle`, `postDate`, `requisitionLocations[].address`, and
  the `ExternalJobID` string field (the number in bc-cfa.org's links,
  used as external_id).
"""

import logging
import re

import httpx

from .base import NormalizedJob, is_data_title

logger = logging.getLogger(__name__)

CID = "1e20e2eb-738c-4c13-b495-ca09f4326217"
FEED_URL = "https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions"
JOB_URL = (
    "https://workforcenow.adp.com/mascsr/default/mdf/recruitment/recruitment.html"
    f"?cid={CID}&ccId=19000101_000001&jobId={{job_id}}&lang=en_CA"
)
PAGE_SIZE = 100
MAX_PAGES = 10
TECH_TITLE_PATTERN = re.compile(
    r"developer|software|programmer|\bIT\b|information technology|cyber|cloud|devops|data|database|network|"
    r"systems? (?:admin|analyst|engineer)|technology|technical support|help ?desk|digital",
    re.IGNORECASE,
)


def scrape() -> list[NormalizedJob]:
    requisitions: list[dict] = []
    with httpx.Client(timeout=30, headers={"User-Agent": "Mozilla/5.0"}) as client:
        for page in range(MAX_PAGES):
            response = client.get(
                FEED_URL,
                params={
                    "cid": CID,
                    "ccId": "19000101_000001",
                    "lang": "en_CA",
                    "locale": "en_CA",
                    "$top": PAGE_SIZE,
                    "$skip": page * PAGE_SIZE,
                },
            )
            response.raise_for_status()
            batch = response.json().get("jobRequisitions") or []
            requisitions.extend(batch)
            if len(batch) < PAGE_SIZE:
                break

    jobs = [
        _normalize(raw)
        for raw in requisitions
        if TECH_TITLE_PATTERN.search(raw.get("requisitionTitle") or "") or is_data_title(raw.get("requisitionTitle") or "")
    ]
    logger.info("BC Centre for Ability: fetched %d matching jobs (of %d postings)", len(jobs), len(requisitions))
    return jobs


def _string_field(raw: dict, code: str) -> str | None:
    for field in (raw.get("customFieldGroup") or {}).get("stringFields") or []:
        if (field.get("nameCode") or {}).get("codeValue") == code:
            return field.get("stringValue")
    return None


def _location(raw: dict) -> str:
    places = []
    for loc in raw.get("requisitionLocations") or []:
        address = loc.get("address") or {}
        city = address.get("cityName")
        region = (address.get("countrySubdivisionLevel1") or {}).get("codeValue")
        if city:
            places.append(f"{city}, {region}" if region else city)
    return "; ".join(dict.fromkeys(places))


def _normalize(raw: dict) -> NormalizedJob:
    job_id = _string_field(raw, "ExternalJobID") or raw["itemID"]
    posted = raw.get("postDate")
    return {
        "external_id": job_id,
        "title": raw["requisitionTitle"].strip(),
        "url": JOB_URL.format(job_id=job_id),
        "location": _location(raw),
        "category": ((raw.get("workLevelCode") or {}).get("shortName")) or "",
        "posted_date": posted[:10] if posted else None,
        "platform": "ADP Workforce Now",
    }
