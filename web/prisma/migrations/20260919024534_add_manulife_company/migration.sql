-- Reference data for the new Manulife scraper (scraper/scrapers/manulife.py)
-- — the scraper's FK insert into "jobs" fails until this row exists, and
-- nothing else in this app creates "companies" rows automatically.
INSERT INTO "companies" ("slug", "name") VALUES ('manulife', 'Manulife')
ON CONFLICT ("slug") DO NOTHING;