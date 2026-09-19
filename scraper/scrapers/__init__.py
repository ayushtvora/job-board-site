from typing import Callable

from .base import NormalizedJob
from . import rbc
from . import soti
from . import ea
from . import bmo
from . import cibc
from . import td
from . import scotiabank
from . import manulife

# Adding a new company: write scrapers/<slug>.py exposing scrape() -> list[NormalizedJob],
# add it here, and add a matching row to the companies table.
SCRAPERS: dict[str, Callable[[], list[NormalizedJob]]] = {
    "rbc": rbc.scrape,
    "soti": soti.scrape,
    "ea": ea.scrape,
    "bmo": bmo.scrape,
    "cibc": cibc.scrape,
    "td": td.scrape,
    "scotiabank": scotiabank.scrape,
    "manulife": manulife.scrape,
}
