from typing import TypedDict


class NormalizedJob(TypedDict):
    external_id: str
    title: str
    url: str
    location: str
    category: str
    posted_date: str | None  # "YYYY-MM-DD", or None if the source doesn't expose one
    platform: str
