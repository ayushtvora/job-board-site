-- Reference data for the Tata Consultancy Services scraper (TCS's own
-- iBegin portal, ibegin.tcsapps.com).
INSERT INTO "companies" ("slug", "name", "sectors") VALUES
    ('tcs', 'Tata Consultancy Services', ARRAY['Consulting & Services'])
ON CONFLICT ("slug") DO NOTHING;
