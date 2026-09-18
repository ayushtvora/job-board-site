-- Reference data for the new BMO, CIBC, TD, and Scotiabank scrapers
-- (scraper/scrapers/{bmo,cibc,td,scotiabank}.py) — each scraper's FK insert
-- into "jobs" fails until its companies row exists, and nothing else in
-- this app creates "companies" rows automatically.
INSERT INTO "companies" ("slug", "name") VALUES
    ('bmo', 'BMO'),
    ('cibc', 'CIBC'),
    ('td', 'TD'),
    ('scotiabank', 'Scotiabank')
ON CONFLICT ("slug") DO NOTHING;