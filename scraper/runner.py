import logging
from datetime import datetime, timezone

from db import get_connection, record_scrape_run, upsert_jobs_and_cleanup
from scrapers import SCRAPERS

logger = logging.getLogger(__name__)


def run_all_scrapers() -> None:
    conn = get_connection()
    try:
        for slug, scrape_fn in SCRAPERS.items():
            _run_for_company(conn, slug, scrape_fn)
    finally:
        conn.close()


def _run_for_company(conn, slug, scrape_fn) -> None:
    started_at = datetime.now(timezone.utc)
    status = "success"
    error_message = None

    try:
        jobs = scrape_fn()
        with conn.transaction():
            upsert_jobs_and_cleanup(conn, slug, jobs)
    except Exception as exc:
        # One company's failure must not stop the others — log it, record it
        # in scrape_runs (so the web UI's error banner can surface it), and
        # move on to the next company.
        logger.exception("%s: scrape failed", slug)
        status = "error"
        error_message = str(exc)[:2000]

    finished_at = datetime.now(timezone.utc)
    record_scrape_run(conn, slug, started_at, finished_at, status, error_message)
