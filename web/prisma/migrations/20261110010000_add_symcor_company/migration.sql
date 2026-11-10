-- Reference data for the Symcor scraper (Dayforce, namespace "symcor").
-- Symcor processes cheques, payments and statements for Canadian banks.
INSERT INTO "companies" ("slug", "name", "sectors") VALUES
    ('symcor', 'Symcor', ARRAY['Fintech & Payments'])
ON CONFLICT ("slug") DO NOTHING;
