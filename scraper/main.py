import argparse
import logging
import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Job board scraper")
    parser.add_argument(
        "--once", action="store_true", help="Run all configured scrapers once immediately, then exit"
    )
    args = parser.parse_args()

    from runner import run_all_scrapers, run_pending_scrape_request

    if args.once:
        run_all_scrapers()
        return

    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger

    tz = ZoneInfo(os.environ.get("TZ", "UTC"))
    scheduler = BlockingScheduler(timezone=tz)
    scheduler.add_job(run_all_scrapers, CronTrigger(hour=6, minute=0, timezone=tz))
    # Short-interval poll for on-demand scans queued via the web app's "Run
    # Job Scan" button (a pending row in scrape_requests) — see
    # run_pending_scrape_request's docstring for why this is poll-based.
    scheduler.add_job(run_pending_scrape_request, IntervalTrigger(seconds=15))
    # next_run_time isn't populated on the Job until the scheduler actually
    # starts, so don't try to read it here — just log the static schedule.
    logger.info("Scheduler starting (daily at 6:00 %s, on-demand scan poll every 15s)", tz)
    scheduler.start()


if __name__ == "__main__":
    main()
