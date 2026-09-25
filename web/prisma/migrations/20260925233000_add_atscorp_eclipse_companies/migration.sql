-- Reference data for ATS Corporation and Eclipse Automation, both unblocked
-- on 2026-09-25 (see CLAUDE.md) — same reasoning as the Manulife migration.
INSERT INTO "companies" ("slug", "name") VALUES
    ('atscorp', 'ATS Corporation'),
    ('eclipse', 'Eclipse Automation')
ON CONFLICT ("slug") DO NOTHING;
