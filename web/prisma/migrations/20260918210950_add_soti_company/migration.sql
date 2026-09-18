-- Reference data for the new SOTI scraper (scraper/scrapers/soti.py) — the
-- scraper's FK insert into "jobs" fails until this row exists, and nothing
-- else in this app creates "companies" rows automatically.
INSERT INTO "companies" ("slug", "name") VALUES ('soti', 'SOTI')
ON CONFLICT ("slug") DO NOTHING;