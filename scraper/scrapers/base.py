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
