import re
from typing import TypedDict

# Matches a Canadian place in a free-text location string, covering every
# province and territory (not just the big tech hubs). Province codes are
# whole-word and case-sensitive (the scoped `(?-i:...)`), so they match
# "Cambridge, ON" but neither "San Francisco, CA" nor the word "on". SK, NL
# and PE are left out as bare codes because they're also the ISO codes for
# Slovakia, the Netherlands and Peru; their province names and main cities
# are matched instead.
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
    r"moncton|st\. john's, nl|charlottetown|whitehorse|yellowknife|iqaluit|kelowna|"
    r"(?-i:\b(?:ON|BC|QC|AB|NS|MB|NB|YT|NT|NU)\b)",
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
