-- "Software" or "Data", for the UI's Field filter. The scraper sets it from
-- the job title on every upsert (job_field in scraper/scrapers/base.py), so
-- existing rows get their real value on the next scrape; until then they
-- show as Software, which is what every job was scoped to before this.
ALTER TABLE "jobs" ADD COLUMN "field" TEXT NOT NULL DEFAULT 'Software';
