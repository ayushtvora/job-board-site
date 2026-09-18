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

    from runner import run_all_scrapers

    if args.once:
        run_all_scrapers()
        return

    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    tz = ZoneInfo(os.environ.get("TZ", "UTC"))
    scheduler = BlockingScheduler(timezone=tz)
    scheduler.add_job(run_all_scrapers, CronTrigger(hour=6, minute=0, timezone=tz))
    # next_run_time isn't populated on the Job until the scheduler actually
    # starts, so don't try to read it here — just log the static schedule.
    logger.info("Scheduler starting (daily at 6:00 %s)", tz)
    scheduler.start()


if __name__ == "__main__":
    main()
