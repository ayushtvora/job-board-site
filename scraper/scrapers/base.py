import re
from typing import TypedDict

# Matches a Canadian place in a free-text location string. Province codes
# are whole-word and case-sensitive (the scoped `(?-i:...)`), so they match
# "Cambridge, ON" but neither "San Francisco, CA" nor the word "on".
CANADA_PATTERN = re.compile(
    r"canada|toronto|vancouver|montr[eé]al|ottawa|waterloo|kitchener|calgary|edmonton|"
    r"oakville|mississauga|burnaby|ontario|british columbia|qu[eé]bec|alberta|"
    r"(?-i:\b(?:ON|BC|QC|AB|NS|MB)\b)",
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
