import html
import re
import threading
from typing import NotRequired, TypedDict

from bs4 import BeautifulSoup

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


# Canadian cities for the UI's Location column and City filter, as
# (display name, pattern). Location strings come in every format
# ("TORONTO, Ontario, Canada", "Toronto, ON, CA, M5H 1H1", "AMER - Canada -
# Ontario - Toronto - University Ave"), so job_cities maps them onto one
# name per city. City names shared with other countries' cities (London,
# Cambridge, Victoria, ...) only match next to a Canadian province.
# Neighbourhoods are folded into their city (Kanata -> Ottawa, North York
# -> Toronto).
_ON = r",?\s*(?:ON\b|Ontario)"
_BC = r",?\s*(?:BC\b|British Columbia)"
_QC = r",?\s*(?:QC\b|Qu[eé]bec)"
CITY_PATTERNS = [
    (name, re.compile(pattern, re.IGNORECASE))
    for name, pattern in [
        ("Toronto", r"toronto|north york|scarborough|etobicoke|don mills"),
        ("Mississauga", r"mississauga"),
        ("Brampton", r"brampton"),
        ("Oakville", r"oakville"),
        ("Burlington", r"burlington" + _ON),
        ("Hamilton", r"hamilton" + _ON),
        ("Markham", r"markham"),
        ("Richmond Hill", r"richmond hill"),
        ("Vaughan", r"vaughan"),
        ("Woodbridge", r"woodbridge" + _ON),
        ("Waterloo", r"waterloo"),
        ("Kitchener", r"kitchener"),
        ("Cambridge", r"cambridge" + _ON),
        ("Guelph", r"guelph"),
        ("London", r"london" + _ON),
        ("Windsor", r"windsor" + _ON),
        ("Kingston", r"kingston" + _ON),
        ("Ottawa", r"ottawa|kanata|nepean"),
        ("Montreal", r"montr[eé]al|saint-laurent|st\.? laurent|verdun"),
        ("Laval", r"\blaval\b"),
        ("Longueuil", r"longueuil"),
        ("Brossard", r"brossard"),
        ("Gatineau", r"gatineau"),
        ("Quebec City", r"qu[eé]bec city|ville de qu[eé]bec|qu[eé]bec" + _QC),
        ("Sherbrooke", r"sherbrooke"),
        ("Vancouver", r"vancouver(?!,?\s*(?:WA\b|Washington))"),
        ("Burnaby", r"burnaby"),
        ("Surrey", r"surrey" + _BC),
        ("Richmond", r"richmond" + _BC),
        ("Victoria", r"victoria(?:" + _BC + r"|,\s*Canada)"),
        ("Kelowna", r"kelowna"),
        ("Calgary", r"calgary"),
        ("Edmonton", r"edmonton"),
        ("Winnipeg", r"winnipeg"),
        ("Regina", r"regina,?\s*(?:SK\b|Saskatchewan)"),
        ("Saskatoon", r"saskatoon"),
        ("Halifax", r"halifax"),
        ("Fredericton", r"fredericton"),
        ("Moncton", r"moncton"),
        ("Saint John", r"saint john(?!')"),
        ("St. John's", r"st\.? john'?s"),
        ("Charlottetown", r"charlottetown"),
        ("Whitehorse", r"whitehorse"),
        ("Yellowknife", r"yellowknife"),
        ("Iqaluit", r"iqaluit"),
    ]
]
# Any other place right before a province ("Kamloops, British Columbia",
# "DORVAL, QC", "Esquimalt (British Columbia)"), for the smaller cities not
# in CITY_PATTERNS. Province codes are case-sensitive and leave out
# NB/NL/PE/SK, for the same reasons as CANADA_PATTERN.
OTHER_CITY_PATTERN = re.compile(
    r"([A-Za-zÀ-ÿ.' -]{3,40}?)\s*(?:,|\()\s*"
    r"(?:(?-i:ON|BC|QC|AB|NS|MB|YT|NT|NU)|ontario|british columbia|qu[eé]bec|alberta|nova scotia|"
    r"manitoba|new brunswick|newfoundland|prince edward island|saskatchewan|yukon|"
    # Not the "Quebec" of "Quebec City".
    r"northwest territories|nunavut)\b(?!\s+city)",
    re.IGNORECASE,
)
NOT_CITY_PATTERN = re.compile(
    r"remote|t[eé]l[eé]travail|home|office|canada|^can$|various|locations?\b|^\W*$", re.IGNORECASE
)
REMOTE_PATTERN = re.compile(r"remote|home[ -]based|virtual|work from home|t[eé]l[eé]travail", re.IGNORECASE)


def job_cities(location: str) -> list[str]:
    """The Canadian cities in a location string, in the order they appear,
    plus "Remote" for remote postings. Empty when the string names no
    city (e.g. just "Canada"); the UI then shows the raw location."""
    found = {}
    for name, pattern in CITY_PATTERNS:
        match = pattern.search(location)
        if match:
            found[name] = match.start()
    for match in OTHER_CITY_PATTERN.finditer(location):
        # Keep only the last part of e.g. "AMER - Canada - Kamloops".
        name = re.split(r"\s+-\s+", match.group(1))[-1].strip(" .-")
        if NOT_CITY_PATTERN.search(name) or CANADA_PATTERN.fullmatch(name):
            continue
        # A street after its number ("8585 Cote-De-Liesse, QC").
        if location[: match.start(1)].rstrip()[-1:].isdigit():
            continue
        if any(pattern.search(name) for _, pattern in CITY_PATTERNS):
            continue
        # "DORVAL" -> "Dorval", leaving mixed-case names like "St-Hyacinthe" as they are.
        name = name.title() if name.isupper() or name.islower() else name
        found.setdefault(name, match.start(1))
    cities = sorted(found, key=found.get)
    if REMOTE_PATTERN.search(location):
        cities.append("Remote")
    return cities


class NormalizedJob(TypedDict):
    external_id: str
    title: str
    url: str
    location: str
    category: str
    posted_date: str | None  # "YYYY-MM-DD", or None if the source doesn't expose one
    platform: str
    # Plain text (see clean_description). Only set by scrapers whose listing
    # response already includes it; for the rest, descriptions.py fetches it
    # once after the job is saved.
    description: NotRequired[str | None]


# Long enough for any real posting; the cap only stops a mis-parsed page
# (a whole site's text) from landing in the database and the scoring prompt.
MAX_DESCRIPTION_CHARS = 20_000
_BLOCK_TAGS = ("p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "ul", "ol", "section")


def clean_description(raw: str | None) -> str | None:
    """A job description (HTML or text, possibly HTML-escaped as Greenhouse
    sends it) as plain text: one line per paragraph or list item, list
    items prefixed with "- ". None when there's no real text."""
    if not raw:
        return None
    text = html.unescape(raw) if "&lt;" in raw else raw
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    for li in soup.find_all("li"):
        li.insert_before("\n- ")
    for tag in soup.find_all(_BLOCK_TAGS):
        tag.insert_after("\n")
    lines = (re.sub(r"[ \t ]+", " ", line).strip() for line in soup.get_text().splitlines())
    cleaned = "\n".join(line for line in lines if line and line != "-")
    cleaned = re.sub(r"\n- \n", "\n- ", cleaned)
    if len(cleaned) < 50:
        return None
    return cleaned[:MAX_DESCRIPTION_CHARS]


# Held by the scrapers that drive a Playwright browser (Meta, Uber) for the
# whole browser session. The runner scrapes companies in parallel, and one
# headless Chromium at a time is plenty for the server.
BROWSER_LOCK = threading.Lock()
