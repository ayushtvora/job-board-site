-- The Canadian cities in each job's location (plus "Remote"), for the UI's
-- Location column and City filter. The scraper sets it from the location
-- on every upsert (job_cities in scraper/scrapers/base.py), so existing
-- rows get their real value on the next scrape; until then the UI shows the
-- raw location.
ALTER TABLE "jobs" ADD COLUMN "cities" TEXT[] NOT NULL DEFAULT '{}';
