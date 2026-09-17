from typing import Callable

from .base import NormalizedJob
from . import rbc

# Adding a new company: write scrapers/<slug>.py exposing scrape() -> list[NormalizedJob],
# add it here, and add a matching row to the companies table.
SCRAPERS: dict[str, Callable[[], list[NormalizedJob]]] = {
    "rbc": rbc.scrape,
}
