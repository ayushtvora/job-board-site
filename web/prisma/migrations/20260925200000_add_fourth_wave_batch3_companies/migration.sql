-- Reference data for the fourth wave's batch 3 of scrapers (see the
-- batch 1 migration / Manulife migration for why these rows are needed).
INSERT INTO "companies" ("slug", "name") VALUES
    ('pinterest', 'Pinterest'),
    ('instacart', 'Instacart'),
    ('coinbase', 'Coinbase'),
    ('nationalbank', 'National Bank'),
    ('intact', 'Intact')
ON CONFLICT ("slug") DO NOTHING;
