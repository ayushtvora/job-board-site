-- Reference data for the new EA scraper (scraper/scrapers/ea.py) — the
-- scraper's FK insert into "jobs" fails until this row exists, and nothing
-- else in this app creates "companies" rows automatically.
INSERT INTO "companies" ("slug", "name") VALUES ('ea', 'EA')
ON CONFLICT ("slug") DO NOTHING;