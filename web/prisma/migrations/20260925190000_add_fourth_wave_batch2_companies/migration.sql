-- Reference data for the fourth wave's batch 2 of scrapers (see the
-- batch 1 migration / Manulife migration for why these rows are needed).
INSERT INTO "companies" ("slug", "name") VALUES
    ('cohere', 'Cohere'),
    ('wealthsimple', 'Wealthsimple'),
    ('faire', 'Faire'),
    ('cloudflare', 'Cloudflare'),
    ('dropbox', 'Dropbox')
ON CONFLICT ("slug") DO NOTHING;
