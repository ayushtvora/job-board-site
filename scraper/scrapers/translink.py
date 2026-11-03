"""TransLink careers scraper (TransLink, BC Rapid Transit Co. and Coast
Mountain Bus Co.; tech roles).

translink.ca/about-us/careers links to a PeopleSoft Candidate Gateway:
`careersconnect.translink.bc.ca/psc/EXT/EMPLOYEE/HRMS/c/HRS_HRAM_FL.HRS_CG_SEARCH_FL.GBL?Page=HRS_APP_SCHJOB_FL&Action=U&FOCUS=Applicant&SiteId=2`.
That GET server-renders the first 50 openings of the full list (no search
needed); ~100 openings across the three companies on 2026-10-02.

- More rows load through PeopleSoft's form postback: POST the page's own
  form (its hidden `IC*` fields) back with `ICAction=HRS_AGNT_RSLT_I$hdown$0`
  and `ICAJAX=1`. Each response re-renders the whole grid with the next
  chunk added, and carries the next `ICStateNum`
  (`ICStateNum.value=N`), which must be sent back on the following POST.
  Paging stops when the row count stops growing.
- Row `i`'s fields have element IDs ending in `$i`: `SCH_JOB_TITLE`,
  `HRS_APP_JBSCH_I_HRS_JOB_OPENING_ID` (external_id), `LOCATION`,
  `HRS_APP_JBSCH_I_HRS_DEPT_DESCR` (department, used as category) and
  `SCH_OPENED` (YYYY/MM/DD).
- There's no tech category, so scope is a title match plus departments
  with "Technology"/"Systems"/"Data" in the name.
- PeopleSoft's job-posting deep link (`Page=HRS_APP_JBPST_FL&JobOpeningId=<id>`)
  only works inside an existing session; opened cold it usually bounces
  back to the job list. So every job links to the job search page, with
  the opening ID as the job ID column to look it up.
"""

import html
import logging
import re

import httpx

from .base import NormalizedJob, is_data_title

logger = logging.getLogger(__name__)

SEARCH_URL = "https://careersconnect.translink.bc.ca/psc/EXT/EMPLOYEE/HRMS/c/HRS_HRAM_FL.HRS_CG_SEARCH_FL.GBL"
SEARCH_PARAMS = {"Page": "HRS_APP_SCHJOB_FL", "Action": "U", "FOCUS": "Applicant", "SiteId": "2"}
JOB_LIST_URL = f"{SEARCH_URL}?Page=HRS_APP_SCHJOB_FL&Action=U&FOCUS=Applicant&SiteId=2"
MAX_POSTBACKS = 20
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"}
HIDDEN_INPUT_RE = re.compile(r"<input type='hidden' name='(IC\w+)' id='\w+' value='([^']*)'")
STATE_NUM_RE = re.compile(r"ICStateNum\.value=(\d+)")
FORM_ACTION_RE = re.compile(r"<form [^>]*action=\"([^\"]+)\"")
TECH_TITLE_PATTERN = re.compile(
    r"developer|software|programmer|\bIT\b|information technology|cyber|cloud|devops|data|database|network|"
    r"systems? (?:admin|analyst|engineer)|machine learning|\bAI\b|solutions? architect|"
    r"technology|technical analyst|\bSCADA\b|\bOT\b",
    re.IGNORECASE,
)
TECH_DEPARTMENT_PATTERN = re.compile(r"technology|systems|data|digital", re.IGNORECASE)


def scrape() -> list[NormalizedJob]:
    with httpx.Client(timeout=60, headers=HEADERS, follow_redirects=True) as client:
        response = client.get(SEARCH_URL, params=SEARCH_PARAMS)
        response.raise_for_status()
        page = response.text
        rows = _rows(page)
        form = dict(HIDDEN_INPUT_RE.findall(page))
        action_match = FORM_ACTION_RE.search(page)
        action = html.unescape(action_match.group(1)) if action_match else SEARCH_URL
        for _ in range(MAX_POSTBACKS):
            response = client.post(action, data=form | {"ICAction": "HRS_AGNT_RSLT_I$hdown$0", "ICAJAX": "1"})
            response.raise_for_status()
            more = _rows(response.text)
            if len(more) <= len(rows):
                break
            rows = more
            state = STATE_NUM_RE.search(response.text)
            if state:
                form["ICStateNum"] = state.group(1)

    if not rows:
        raise RuntimeError("TransLink job search returned no openings; the page layout may have changed")
    jobs = [
        job for job in rows.values()
        if TECH_TITLE_PATTERN.search(job["title"])
        or TECH_DEPARTMENT_PATTERN.search(job["category"])
        or is_data_title(job["title"])
    ]
    logger.info("TransLink: fetched %d matching jobs (of %d openings)", len(jobs), len(rows))
    return jobs


def _field(page: str, element: str, index: str) -> str:
    match = re.search(rf"id='{element}\${index}'[^>]*>([^<]*)<", page)
    return html.unescape(match.group(1)).strip() if match else ""


def _rows(page: str) -> dict[str, NormalizedJob]:
    rows: dict[str, NormalizedJob] = {}
    for index in re.findall(r"id='HRS_APP_JBSCH_I_HRS_JOB_OPENING_ID\$(\d+)'", page):
        opening_id = _field(page, "HRS_APP_JBSCH_I_HRS_JOB_OPENING_ID", index)
        if not opening_id:
            continue
        opened = _field(page, "SCH_OPENED", index)
        rows[opening_id] = {
            "external_id": opening_id,
            "title": _field(page, "SCH_JOB_TITLE", index),
            "url": JOB_LIST_URL,
            "location": _field(page, "LOCATION", index),
            "category": _field(page, "HRS_APP_JBSCH_I_HRS_DEPT_DESCR", index),
            "posted_date": opened.replace("/", "-") if re.fullmatch(r"\d{4}/\d{2}/\d{2}", opened) else None,
            "platform": "PeopleSoft",
        }
    return rows
