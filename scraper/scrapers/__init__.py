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
from . import nvidia
from . import ubc
from . import sony
from . import intel
from . import blizzard
from . import adobe
from . import snowflake
from . import riotgames
from . import reddit
from . import airbnb
from . import databricks
from . import stripe
from . import canonical
from . import spotify
from . import libertymutual
from . import microsoft
from . import oracle
from . import metrolinx
from . import amazon
from . import google
from . import apple
from . import ibm
from . import sap
from . import meta
from . import shopify
from . import thomsonreuters
from . import salesforce
from . import sunlife
from . import cohere
from . import wealthsimple
from . import faire
from . import cloudflare
from . import dropbox
from . import pinterest
from . import instacart
from . import coinbase
from . import nationalbank
from . import intact
from . import canadalife
from . import questrade
from . import interac
from . import rogers
from . import bell
from . import telus
from . import ubisoft
from . import clio
from . import onepassword
from . import kinaxis
from . import opentext
from . import geotab
from . import d2l
from . import arcticwolf
from . import workdayinc
from . import atscorp
from . import eclipse

# Adding a new company: write scrapers/<slug>.py exposing scrape() -> list[NormalizedJob],
# add it here, and add a matching row to the companies table. Companies on a
# common ATS can use the shared helpers (workday_cxs, greenhouse, ashby,
# jobs2web, phenom, dayforce) so their module is just config + notes.
SCRAPERS: dict[str, Callable[[], list[NormalizedJob]]] = {
    "rbc": rbc.scrape,
    "soti": soti.scrape,
    "ea": ea.scrape,
    "bmo": bmo.scrape,
    "cibc": cibc.scrape,
    "td": td.scrape,
    "scotiabank": scotiabank.scrape,
    "manulife": manulife.scrape,
    "nvidia": nvidia.scrape,
    "ubc": ubc.scrape,
    "sony": sony.scrape,
    "intel": intel.scrape,
    "blizzard": blizzard.scrape,
    "adobe": adobe.scrape,
    "snowflake": snowflake.scrape,
    "riotgames": riotgames.scrape,
    "reddit": reddit.scrape,
    "airbnb": airbnb.scrape,
    "databricks": databricks.scrape,
    "stripe": stripe.scrape,
    "canonical": canonical.scrape,
    "spotify": spotify.scrape,
    "libertymutual": libertymutual.scrape,
    "microsoft": microsoft.scrape,
    "oracle": oracle.scrape,
    "metrolinx": metrolinx.scrape,
    "amazon": amazon.scrape,
    "google": google.scrape,
    "apple": apple.scrape,
    "ibm": ibm.scrape,
    "sap": sap.scrape,
    "meta": meta.scrape,
    "shopify": shopify.scrape,
    "thomsonreuters": thomsonreuters.scrape,
    "salesforce": salesforce.scrape,
    "sunlife": sunlife.scrape,
    "cohere": cohere.scrape,
    "wealthsimple": wealthsimple.scrape,
    "faire": faire.scrape,
    "cloudflare": cloudflare.scrape,
    "dropbox": dropbox.scrape,
    "pinterest": pinterest.scrape,
    "instacart": instacart.scrape,
    "coinbase": coinbase.scrape,
    "nationalbank": nationalbank.scrape,
    "intact": intact.scrape,
    "canadalife": canadalife.scrape,
    "questrade": questrade.scrape,
    "interac": interac.scrape,
    "rogers": rogers.scrape,
    "bell": bell.scrape,
    "telus": telus.scrape,
    "ubisoft": ubisoft.scrape,
    "clio": clio.scrape,
    "1password": onepassword.scrape,
    "kinaxis": kinaxis.scrape,
    "opentext": opentext.scrape,
    "geotab": geotab.scrape,
    "d2l": d2l.scrape,
    "arcticwolf": arcticwolf.scrape,
    "workday": workdayinc.scrape,
    "atscorp": atscorp.scrape,
    "eclipse": eclipse.scrape,
}
