-- Company groups for the UI's "Sector" filter. Free text like jobs.category;
-- a company added later without sectors shows up under "Other" until a
-- migration assigns it some.
--
-- Each company gets its main sector first, and then a second one further
-- down only where a good share of its engineering roles fit that sector
-- too. Being loosely related isn't enough, or the sectors stop filtering
-- anything (every tech company claims some AI).
ALTER TABLE "companies" ADD COLUMN     "sectors" TEXT[] DEFAULT ARRAY['Other']::TEXT[];

UPDATE "companies" SET "sectors" = ARRAY['Banking'] WHERE "slug" IN (
    'rbc', 'bmo', 'cibc', 'td', 'scotiabank', 'nationalbank', 'desjardins',
    'eqbank', 'atb'
);

UPDATE "companies" SET "sectors" = ARRAY['Insurance'] WHERE "slug" IN (
    'manulife', 'sunlife', 'canadalife', 'intact', 'definity',
    'libertymutual', 'bcaa'
);

UPDATE "companies" SET "sectors" = ARRAY['Fintech & Payments'] WHERE "slug" IN (
    'wealthsimple', 'questrade', 'koho', 'neo', 'coinbase', 'affirm',
    'stripe', 'paypal', 'mastercard', 'amex', 'interac'
);

UPDATE "companies" SET "sectors" = ARRAY['Trading & Investment'] WHERE "slug" IN (
    'hrt', 'janestreet', 'optiver', 'twosigma', 'cppinvestments', 'omers',
    'otpp'
);

UPDATE "companies" SET "sectors" = ARRAY['Government & Public Sector'] WHERE "slug" IN (
    'govcanada', 'statcan', 'nrc', 'govbc', 'cityoftoronto', 'bankofcanada',
    'metrolinx', 'translink', 'hydroone', 'ubc', 'nasa', 'bccfa'
);

UPDATE "companies" SET "sectors" = ARRAY['Gaming & Entertainment'] WHERE "slug" IN (
    'ea', 'ubisoft', 'blizzard', 'riotgames', 'cdprojektred', 'playstation',
    'sony', 'netflix', 'spotify'
);

UPDATE "companies" SET "sectors" = ARRAY['Big Tech'] WHERE "slug" IN (
    'google', 'apple', 'meta', 'amazon', 'microsoft'
);

UPDATE "companies" SET "sectors" = ARRAY['AI'] WHERE "slug" IN (
    'anthropic', 'openai', 'cohere', 'waabi', 'xanadu'
);

UPDATE "companies" SET "sectors" = ARRAY['Hardware & Semiconductors'] WHERE "slug" IN (
    'nvidia', 'intel', 'amd', 'qualcomm', 'cadence', 'synopsys',
    'tenstorrent', 'celestica'
);

UPDATE "companies" SET "sectors" = ARRAY['Cybersecurity'] WHERE "slug" IN (
    'fortinet', 'arcticwolf', '1password', 'okta', 'blackberry'
);

UPDATE "companies" SET "sectors" = ARRAY['Telecom & Networking'] WHERE "slug" IN (
    'bell', 'rogers', 'telus', 'cisco', 'ciena', 'nokia', 'ericsson',
    'arista'
);

UPDATE "companies" SET "sectors" = ARRAY['Enterprise Software & Cloud'] WHERE "slug" IN (
    'oracle', 'sap', 'ibm', 'salesforce', 'workday', 'adobe', 'autodesk',
    'opentext', 'snowflake', 'databricks', 'datadog', 'cloudflare',
    'twilio', 'canonical', 'intuit', 'thomsonreuters', 'kinaxis', 'soti',
    'samsara', 'geotab', 'dropbox', 'asana', 'figma'
);

UPDATE "companies" SET "sectors" = ARRAY['Startups & Scale-ups'] WHERE "slug" IN (
    'd2l', 'clio', 'vidyard', 'freshbooks', 'jobber', 'loopio', 'thinkific',
    'benevity', 'league', 'ada', 'stackadapt', 'applyboard', 'faire',
    'ycombinator'
);

UPDATE "companies" SET "sectors" = ARRAY['Consumer Internet'] WHERE "slug" IN (
    'shopify', 'uber', 'lyft', 'airbnb', 'doordash', 'instacart',
    'pinterest', 'reddit', 'hopper'
);

UPDATE "companies" SET "sectors" = ARRAY['Consulting & Services'] WHERE "slug" IN (
    'accenture', 'deloitte', 'ey', 'kpmgus', 'devit'
);

UPDATE "companies" SET "sectors" = ARRAY['Industrial, Retail & Transportation'] WHERE "slug" IN (
    'aircanada', 'gm', 'cae', 'eclipse', 'atscorp', 'canadiantire', 'loblaw'
);

-- Second sectors.
UPDATE "companies" SET "sectors" = "sectors" || ARRAY['Insurance'] WHERE "slug" = 'desjardins';
UPDATE "companies" SET "sectors" = "sectors" || ARRAY['Fintech & Payments'] WHERE "slug" = 'eqbank';
UPDATE "companies" SET "sectors" = "sectors" || ARRAY['Banking'] WHERE "slug" IN ('amex', 'bankofcanada');
UPDATE "companies" SET "sectors" = "sectors" || ARRAY['AI'] WHERE "slug" IN (
    'google', 'meta', 'microsoft', 'nvidia', 'tenstorrent'
);
UPDATE "companies" SET "sectors" = "sectors" || ARRAY['Big Tech'] WHERE "slug" = 'nvidia';
UPDATE "companies" SET "sectors" = "sectors" || ARRAY['Hardware & Semiconductors'] WHERE "slug" IN (
    'sony', 'blackberry', 'xanadu'
);
UPDATE "companies" SET "sectors" = "sectors" || ARRAY['Cybersecurity'] WHERE "slug" = 'cloudflare';
UPDATE "companies" SET "sectors" = "sectors" || ARRAY['Industrial, Retail & Transportation'] WHERE "slug" = 'waabi';
