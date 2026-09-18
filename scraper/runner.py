import logging
from datetime import datetime, timezone

from db import (
    claim_pending_scrape_request,
    finish_scrape_request,
    get_connection,
    record_scrape_run,
    upsert_jobs_and_cleanup,
)
from scrapers import SCRAPERS

logger = logging.getLogger(__name__)


def run_all_scrapers() -> None:
    conn = get_connection()
    try:
        for slug, scrape_fn in SCRAPERS.items():
            _run_for_company(conn, slug, scrape_fn)
    finally:
        conn.close()


def run_pending_scrape_request() -> None:
    """Check Postgres for an on-demand scan request queued by the web app's
    "Run Job Scan" button, and run one if found. Polled on a short interval
    by the scheduler alongside the daily cron job — this is the only channel
    the web app has to trigger a scan, since web and scraper never call each
    other directly (see CLAUDE.md).
    """
    conn = get_connection()
    try:
        request_id = claim_pending_scrape_request(conn)
    finally:
        conn.close()

    if request_id is None:
        return

    logger.info("Running on-demand scrape (request #%s)", request_id)
    error_message = None
    try:
        run_all_scrapers()
    except Exception as exc:
        # Per-company failures are already caught in _run_for_company; this
        # only catches something breaking the request itself (e.g. the
        # initial DB connection).
        logger.exception("On-demand scrape request #%s failed", request_id)
        error_message = str(exc)[:2000]

    conn = get_connection()
    try:
        finish_scrape_request(conn, request_id, "error" if error_message else "done", error_message)
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
