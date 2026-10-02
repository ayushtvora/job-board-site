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
from . import autodesk
from . import ada
from . import league
from . import tenstorrent
from . import doordash
from . import lyft
from . import okta
from . import asana
from . import samsara
from . import twilio
from . import affirm
from . import figma
from . import datadog
from . import jobber
from . import neo
from . import koho
from . import benevity
from . import hopper
from . import loopio
from . import thinkific
from . import waabi
from . import eqbank
from . import cisco
from . import ciena
from . import paypal
from . import mastercard
from . import cppinvestments
from . import omers
from . import otpp
from . import desjardins
from . import loblaw
from . import canadiantire
from . import cae
from . import applyboard
from . import blackberry
from . import cadence
from . import qualcomm
from . import ericsson
from . import atb
from . import nokia
from . import definity
from . import fortinet
from . import aircanada
from . import celestica
from . import hydroone
from . import cityoftoronto
from . import bankofcanada
from . import arista
from . import intuit
from . import synopsys
from . import xanadu
from . import vidyard
from . import freshbooks
from . import stackadapt
from . import anthropic
from . import openai
from . import playstation
from . import cdprojektred
from . import hrt
from . import janestreet
from . import optiver
from . import twosigma
from . import gm
from . import accenture
from . import bcaa
from . import amex
from . import netflix
from . import ey
from . import deloitte
from . import kpmgus
from . import govcanada
from . import statcan
from . import nrc
from . import govbc
from . import translink
from . import bccfa
from . import devit
from . import nasa
from . import ycombinator
from . import uber
from . import amd

# Adding a new company: write scrapers/<slug>.py exposing scrape() -> list[NormalizedJob],
# add it here, and add a matching row to the companies table. Companies on a
# common ATS should use the shared helper for it (workday_cxs, greenhouse,
# ashby, lever, jobs2web, phenom, eightfold, oracle_recruiting, dayforce,
# smartrecruiters, talentbrew, jibe, gcjobs), so
# their module is just config + investigation notes.
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
    "autodesk": autodesk.scrape,
    "ada": ada.scrape,
    "league": league.scrape,
    "tenstorrent": tenstorrent.scrape,
    "doordash": doordash.scrape,
    "lyft": lyft.scrape,
    "okta": okta.scrape,
    "asana": asana.scrape,
    "samsara": samsara.scrape,
    "twilio": twilio.scrape,
    "affirm": affirm.scrape,
    "figma": figma.scrape,
    "datadog": datadog.scrape,
    "jobber": jobber.scrape,
    "neo": neo.scrape,
    "koho": koho.scrape,
    "benevity": benevity.scrape,
    "hopper": hopper.scrape,
    "loopio": loopio.scrape,
    "thinkific": thinkific.scrape,
    "waabi": waabi.scrape,
    "eqbank": eqbank.scrape,
    "cisco": cisco.scrape,
    "ciena": ciena.scrape,
    "paypal": paypal.scrape,
    "mastercard": mastercard.scrape,
    "cppinvestments": cppinvestments.scrape,
    "omers": omers.scrape,
    "otpp": otpp.scrape,
    "desjardins": desjardins.scrape,
    "loblaw": loblaw.scrape,
    "canadiantire": canadiantire.scrape,
    "cae": cae.scrape,
    "applyboard": applyboard.scrape,
    "blackberry": blackberry.scrape,
    "cadence": cadence.scrape,
    "qualcomm": qualcomm.scrape,
    "ericsson": ericsson.scrape,
    "atb": atb.scrape,
    "nokia": nokia.scrape,
    "definity": definity.scrape,
    "fortinet": fortinet.scrape,
    "aircanada": aircanada.scrape,
    "celestica": celestica.scrape,
    "hydroone": hydroone.scrape,
    "cityoftoronto": cityoftoronto.scrape,
    "bankofcanada": bankofcanada.scrape,
    "arista": arista.scrape,
    "intuit": intuit.scrape,
    "synopsys": synopsys.scrape,
    "xanadu": xanadu.scrape,
    "vidyard": vidyard.scrape,
    "freshbooks": freshbooks.scrape,
    "stackadapt": stackadapt.scrape,
    "anthropic": anthropic.scrape,
    "openai": openai.scrape,
    "playstation": playstation.scrape,
    "cdprojektred": cdprojektred.scrape,
    "hrt": hrt.scrape,
    "janestreet": janestreet.scrape,
    "optiver": optiver.scrape,
    "twosigma": twosigma.scrape,
    "gm": gm.scrape,
    "accenture": accenture.scrape,
    "bcaa": bcaa.scrape,
    "amex": amex.scrape,
    "netflix": netflix.scrape,
    "ey": ey.scrape,
    "deloitte": deloitte.scrape,
    "kpmgus": kpmgus.scrape,
    "govcanada": govcanada.scrape,
    "statcan": statcan.scrape,
    "nrc": nrc.scrape,
    "govbc": govbc.scrape,
    "translink": translink.scrape,
    "bccfa": bccfa.scrape,
    "devit": devit.scrape,
    "nasa": nasa.scrape,
    "ycombinator": ycombinator.scrape,
    "uber": uber.scrape,
    "amd": amd.scrape,
}
