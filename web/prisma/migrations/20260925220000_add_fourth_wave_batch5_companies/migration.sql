-- Reference data for the fourth wave's batch 5 of scrapers (see the
-- batch 1 migration / Manulife migration for why these rows are needed).
INSERT INTO "companies" ("slug", "name") VALUES
    ('telus', 'TELUS'),
    ('ubisoft', 'Ubisoft'),
    ('clio', 'Clio'),
    ('1password', '1Password'),
    ('kinaxis', 'Kinaxis')
ON CONFLICT ("slug") DO NOTHING;
