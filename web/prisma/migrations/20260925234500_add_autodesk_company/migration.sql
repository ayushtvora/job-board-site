-- Reference data for the Autodesk scraper (Eightfold, jobs.autodesk.com) —
-- same reasoning as the Manulife migration.
INSERT INTO "companies" ("slug", "name") VALUES
    ('autodesk', 'Autodesk')
ON CONFLICT ("slug") DO NOTHING;
