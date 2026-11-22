-- Reference data for the Siemens (Avature), JPMorgan Chase (Oracle
-- Recruiting Cloud, Canada + US) and KPMG Canada (iCIMS Jibe) scrapers. I
-- have a referral at the latter two (see src/lib/referral.ts). KPMG US
-- ('kpmgus') is a separate member firm and isn't flagged.
INSERT INTO "companies" ("slug", "name", "sectors", "referral") VALUES
    ('siemens', 'Siemens', ARRAY['Industrial, Retail & Transportation'], false),
    ('jpmorgan', 'JPMorgan Chase', ARRAY['Banking'], true),
    ('kpmg', 'KPMG', ARRAY['Consulting & Services'], true)
ON CONFLICT ("slug") DO NOTHING;
