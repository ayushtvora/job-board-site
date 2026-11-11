-- Reference data for the seventh wave of scrapers (2026-11-10): companies
-- with data and software roles in Toronto and Vancouver. Sectors follow
-- the same rules as 20261102000000_add_company_sector; "Healthcare & Life
-- Sciences" is new, for the hospitals, health-data agencies and biotech.
INSERT INTO "companies" ("slug", "name", "sectors") VALUES
    ('capitalone', 'Capital One', ARRAY['Banking']),
    ('citi', 'Citi', ARRAY['Banking']),
    ('equifax', 'Equifax', ARRAY['Fintech & Payments']),
    ('transunion', 'TransUnion', ARRAY['Fintech & Payments']),
    ('morningstar', 'Morningstar', ARRAY['Trading & Investment']),
    ('allstate', 'Allstate', ARRAY['Insurance']),
    ('aviva', 'Aviva', ARRAY['Insurance']),
    ('moneris', 'Moneris', ARRAY['Fintech & Payments']),
    ('brookfield', 'Brookfield', ARRAY['Trading & Investment']),
    ('kobo', 'Rakuten Kobo', ARRAY['Consumer Internet']),
    ('fidelitycanada', 'Fidelity Canada', ARRAY['Trading & Investment']),
    ('ontariohealth', 'Ontario Health', ARRAY['Government & Public Sector', 'Healthcare & Life Sciences']),
    ('samsung', 'Samsung', ARRAY['Hardware & Semiconductors', 'AI']),
    ('block', 'Block', ARRAY['Fintech & Payments']),
    ('later', 'Later', ARRAY['Startups & Scale-ups']),
    ('abcellera', 'AbCellera', ARRAY['Healthcare & Life Sciences']),
    ('hootsuite', 'Hootsuite', ARRAY['Enterprise Software & Cloud']),
    ('lgairesearch', 'LG AI Research', ARRAY['AI']),
    ('float', 'Float', ARRAY['Fintech & Payments']),
    ('visier', 'Visier', ARRAY['Enterprise Software & Cloud']),
    ('wattpad', 'Wattpad', ARRAY['Consumer Internet']),
    ('nielseniq', 'NielsenIQ', ARRAY['Consulting & Services']),
    ('uhn', 'University Health Network', ARRAY['Healthcare & Life Sciences']),
    ('icbc', 'ICBC', ARRAY['Insurance', 'Government & Public Sector']),
    ('uoft', 'University of Toronto', ARRAY['Government & Public Sector']),
    ('lululemon', 'lululemon', ARRAY['Industrial, Retail & Transportation']),
    ('dwave', 'D-Wave', ARRAY['Hardware & Semiconductors']),
    ('ices', 'ICES', ARRAY['Healthcare & Life Sciences', 'Government & Public Sector'])
ON CONFLICT ("slug") DO NOTHING;

-- The Loblaw scraper now reads all of Loblaw Companies' tech and data
-- postings (careers.loblaw.ca), not just Loblaw Digital's.
UPDATE "companies" SET "name" = 'Loblaw' WHERE "slug" = 'loblaw';
