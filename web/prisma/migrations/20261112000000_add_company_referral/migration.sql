-- Companies where I have a referral (see src/lib/referral.ts): their jobs
-- get a score bonus in the table and are scored sooner. The Government of
-- Ontario isn't scraped (gojobs.gov.on.ca is behind a bot challenge), so
-- it has no row to flag.
ALTER TABLE "companies" ADD COLUMN "referral" BOOLEAN NOT NULL DEFAULT false;

UPDATE "companies" SET "referral" = true WHERE "slug" IN (
    'rbc', 'manulife', 'libertymutual', 'mars', 'eclipse', 'atscorp',
    'accenture', 'bccfa', 'devit', 'metrolinx', 'tcs', 'symcor'
);
