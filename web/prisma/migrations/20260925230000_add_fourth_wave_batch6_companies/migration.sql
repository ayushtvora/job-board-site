-- Reference data for the fourth wave's batch 6 of scrapers (see the
-- batch 1 migration / Manulife migration for why these rows are needed).
INSERT INTO "companies" ("slug", "name") VALUES
    ('opentext', 'OpenText'),
    ('geotab', 'Geotab'),
    ('d2l', 'D2L'),
    ('arcticwolf', 'Arctic Wolf'),
    ('workday', 'Workday')
ON CONFLICT ("slug") DO NOTHING;
