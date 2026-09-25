-- Reference data for the third (hardest-tier) wave of scrapers added from
-- CLAUDE.md's "Current scope" investigations — each scraper's FK insert into
-- "jobs" fails until its "companies" row exists, and nothing else in this
-- app creates "companies" rows automatically (see the Manulife migration for
-- the same reasoning).
INSERT INTO "companies" ("slug", "name") VALUES
    ('amazon', 'Amazon'),
    ('google', 'Google'),
    ('apple', 'Apple'),
    ('ibm', 'IBM'),
    ('sap', 'SAP'),
    ('meta', 'Meta')
ON CONFLICT ("slug") DO NOTHING;
