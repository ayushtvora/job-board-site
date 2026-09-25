-- Reference data for the second wave of scrapers (scraper/scrapers/*.py) added
-- from CLAUDE.md's "Current scope" investigations — each scraper's FK insert
-- into "jobs" fails until its "companies" row exists, and nothing else in
-- this app creates "companies" rows automatically (see the Manulife
-- migration for the same reasoning).
INSERT INTO "companies" ("slug", "name") VALUES
    ('nvidia', 'Nvidia'),
    ('ubc', 'UBC'),
    ('sony', 'Sony'),
    ('intel', 'Intel'),
    ('blizzard', 'Blizzard'),
    ('adobe', 'Adobe'),
    ('snowflake', 'Snowflake'),
    ('riotgames', 'Riot Games'),
    ('reddit', 'Reddit'),
    ('airbnb', 'Airbnb'),
    ('databricks', 'Databricks'),
    ('stripe', 'Stripe'),
    ('canonical', 'Canonical'),
    ('spotify', 'Spotify'),
    ('libertymutual', 'Liberty Mutual'),
    ('microsoft', 'Microsoft'),
    ('oracle', 'Oracle'),
    ('metrolinx', 'Metrolinx')
ON CONFLICT ("slug") DO NOTHING;
