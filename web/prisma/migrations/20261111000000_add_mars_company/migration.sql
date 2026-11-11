-- Reference data for the Mars, Incorporated scraper (Workday,
-- mars.wd3.myworkdayjobs.com/External).
INSERT INTO "companies" ("slug", "name", "sectors") VALUES
    ('mars', 'Mars', ARRAY['Industrial, Retail & Transportation'])
ON CONFLICT ("slug") DO NOTHING;
