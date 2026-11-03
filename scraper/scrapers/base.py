import re
import threading
from typing import TypedDict

# Matches a Canadian place in a free-text location string, covering every
# province and territory (not just the big tech hubs). Province codes are
# whole-word and case-sensitive (the scoped `(?-i:...)`), so they match
# "Cambridge, ON" but neither "San Francisco, CA" nor the word "on". SK, NL
# and PE are left out as bare codes because they're also the ISO codes for
# Slovakia, the Netherlands and Peru, and NB because it's the Dutch province
# Noord-Brabant ("Breda, NB, NL"); their province names and main cities are
# matched instead.
CANADA_PATTERN = re.compile(
    r"canada|"
    # Provinces and territories
    r"ontario|british columbia|qu[eé]bec|alberta|saskatchewan|manitoba|nova scotia|"
    r"new brunswick|newfoundland|labrador|prince edward island|yukon|"
    r"northwest territories|nunavut|"
    # Cities
    r"toronto|vancouver|montr[eé]al|ottawa|waterloo|kitchener|calgary|edmonton|"
    r"oakville|mississauga|burnaby|markham|brampton|kanata|richmond hill|guelph|"
    r"gatineau|laval|sherbrooke|winnipeg|halifax|saskatoon|regina, sk|fredericton|"
    r"moncton|saint john, nb|st\. john's, nl|charlottetown|whitehorse|yellowknife|"
    r"iqaluit|kelowna|"
    r"(?-i:\b(?:ON|BC|QC|AB|NS|MB|YT|NT|NU)\b)",
    re.IGNORECASE,
)


# Data roles (data scientist/engineer/analyst, analytics, BI, statistics),
# matched on the job title. Every scraper keeps Canadian jobs with a data
# title even when they fall outside its software scope, so each company's
# data roles get picked up; and db.py sets each job's `field` from it (see
# job_field). "BI" is case-sensitive so it doesn't match "bi-weekly".
DATA_TITLE_PATTERN = re.compile(
    r"\bdata\b|analytics|business intel|(?-i:\bBI\b)|power ?bi|tableau|\bETL\b|statistici|statistical|"
    r"insights? (?:analyst|specialist)|donn[ée]es",
    re.IGNORECASE,
)
# Titles that mention data but aren't data roles: data centres, clerical
# and annotation work, and sales/legal/product roles named after a data
# product ("Data Platform Sales Representative").
NOT_DATA_TITLE_PATTERN = re.compile(
    r"data[ -]?cent(?:er|re)|data entry|data protection|data privacy|annotat|data label|data collection|"
    r"\bsales\b|account (?:executive|manager)|counsel|\blegal\b|assistant|recruit|product manager",
    re.IGNORECASE,
)
# Free-text search terms for the sites that filter by category on the
# server, so data roles need a separate keyword search (results are then
# kept only if the title passes is_data_title).
DATA_SEARCH_TERMS = ("data", "analytics")


def is_data_title(title: str) -> bool:
    return bool(DATA_TITLE_PATTERN.search(title)) and not NOT_DATA_TITLE_PATTERN.search(title)


def job_field(title: str) -> str:
    """"Data" or "Software", for the UI's Field filter. A data title that
    also says "software" ("Software Engineer, Data Platform") is software."""
    if is_data_title(title) and "software" not in title.lower():
        return "Data"
    return "Software"


class NormalizedJob(TypedDict):
    external_id: str
    title: str
    url: str
    location: str
    category: str
    posted_date: str | None  # "YYYY-MM-DD", or None if the source doesn't expose one
    platform: str


# Held by the scrapers that drive a Playwright browser (Meta, Uber) for the
# whole browser session. The runner scrapes companies in parallel, and one
# headless Chromium at a time is plenty for the server.
BROWSER_LOCK = threading.Lock()
