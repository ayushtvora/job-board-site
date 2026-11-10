import logging
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone

import host_limits
from descriptions import fetch_missing_descriptions
from db import (
    claim_pending_scrape_request,
    finish_scrape_request,
    get_connection,
    record_scrape_run,
    upsert_jobs_and_cleanup,
)
from scrapers import SCRAPERS
from scrapers.base import NormalizedJob

logger = logging.getLogger(__name__)

# Companies scraped at once. Scraping is almost all waiting on the network,
# so threads are enough; host_limits keeps companies on a shared ATS host
# from piling onto it.
MAX_WORKERS = 16


@dataclass
class ScrapeResult:
    slug: str
    started_at: datetime
    finished_at: datetime
    jobs: list[NormalizedJob] | None
    error: str | None


def run_all_scrapers(only: list[str] | None = None) -> None:
    """Scrape every company (or just the slugs in `only`), then fetch the
    descriptions of jobs saved without one."""
    scrapers = SCRAPERS
    if only:
        unknown = set(only) - set(SCRAPERS)
        if unknown:
            raise ValueError(f"Unknown company slug(s): {', '.join(sorted(unknown))}")
        scrapers = {slug: SCRAPERS[slug] for slug in only}

    conn = get_connection()
    try:
        # Only the scraping runs in parallel. Results are written here, one
        # company at a time, so the connection is never shared between
        # threads.
        for result in scrape_companies(scrapers):
            _save_result(conn, result)
        # Descriptions are only for the web app's scoring, so a failure here
        # is logged, not recorded as a failed scrape.
        try:
            fetch_missing_descriptions(conn)
        except Exception:
            logger.exception("Fetching job descriptions failed")
            conn.rollback()
    finally:
        conn.close()


def scrape_companies(scrapers: dict[str, Callable[[], list[NormalizedJob]]]) -> Iterator[ScrapeResult]:
    """Run every scraper in a thread pool, yielding each result as it finishes."""
    host_limits.install()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="scrape") as pool:
        futures = [pool.submit(_scrape_company, slug, scrape_fn) for slug, scrape_fn in scrapers.items()]
        for future in as_completed(futures):
            yield future.result()


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
        # Per-company failures are already caught in _scrape_company and
        # _save_result; this only catches something breaking the request
        # itself (e.g. the initial DB connection).
        logger.exception("On-demand scrape request #%s failed", request_id)
        error_message = str(exc)[:2000]

    conn = get_connection()
    try:
        finish_scrape_request(conn, request_id, "error" if error_message else "done", error_message)
    finally:
        conn.close()


def _scrape_company(slug: str, scrape_fn: Callable[[], list[NormalizedJob]]) -> ScrapeResult:
    started_at = datetime.now(timezone.utc)
    jobs = None
    error_message = None
    try:
        jobs = scrape_fn()
    except Exception as exc:
        # One company's failure must not stop the others — log it, record it
        # in scrape_runs (so the web UI's error banner can surface it), and
        # move on to the next company.
        logger.exception("%s: scrape failed", slug)
        error_message = str(exc)[:2000]
    return ScrapeResult(slug, started_at, datetime.now(timezone.utc), jobs, error_message)


def _save_result(conn, result: ScrapeResult) -> None:
    error_message = result.error
    if error_message is None:
        try:
            with conn.transaction():
                upsert_jobs_and_cleanup(conn, result.slug, result.jobs)
        except Exception as exc:
            logger.exception("%s: saving jobs failed", result.slug)
            error_message = str(exc)[:2000]

    status = "error" if error_message else "success"
    record_scrape_run(conn, result.slug, result.started_at, result.finished_at, status, error_message)
