-- Reference data for the fourth wave's batch 4 of scrapers (see the
-- batch 1 migration / Manulife migration for why these rows are needed).
INSERT INTO "companies" ("slug", "name") VALUES
    ('canadalife', 'Canada Life'),
    ('questrade', 'Questrade'),
    ('interac', 'Interac'),
    ('rogers', 'Rogers'),
    ('bell', 'Bell')
ON CONFLICT ("slug") DO NOTHING;
