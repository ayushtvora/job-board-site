-- Reference data for the fourth wave's first batch of scrapers — each
-- scraper's FK insert into "jobs" fails until its "companies" row exists
-- (see the Manulife migration for the same reasoning).
INSERT INTO "companies" ("slug", "name") VALUES
    ('shopify', 'Shopify'),
    ('thomsonreuters', 'Thomson Reuters'),
    ('salesforce', 'Salesforce'),
    ('sunlife', 'Sun Life')
ON CONFLICT ("slug") DO NOTHING;
