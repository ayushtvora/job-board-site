-- AI relevance scoring (see CLAUDE.md "Relevance score").
--
-- description / description_attempts are written only by the scraper
-- (each job's description is fetched once, when it's first seen). The
-- score* columns, matched/missing skills and the resumes/scoring_state
-- tables are written only by the web app's scoring worker.
ALTER TABLE "jobs" ADD COLUMN "description" TEXT;
ALTER TABLE "jobs" ADD COLUMN "description_attempts" INTEGER NOT NULL DEFAULT 0;
ALTER TABLE "jobs" ADD COLUMN "score" INTEGER;
ALTER TABLE "jobs" ADD COLUMN "score_reason" TEXT;
ALTER TABLE "jobs" ADD COLUMN "matched_skills" TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE "jobs" ADD COLUMN "missing_skills" TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE "jobs" ADD COLUMN "score_basis" TEXT;
ALTER TABLE "jobs" ADD COLUMN "score_key" TEXT;
ALTER TABLE "jobs" ADD COLUMN "scored_at" TIMESTAMP(3);

-- One resume per jobs.field ("Software" / "Data"), fetched from
-- RESUME_URL_SOFTWARE / RESUME_URL_DATA.
CREATE TABLE "resumes" (
    "field" TEXT NOT NULL,
    "text" TEXT NOT NULL,
    "hash" TEXT NOT NULL,
    "fetched_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "resumes_pkey" PRIMARY KEY ("field")
);

-- Single row (id = 1): the scoring worker's last error, for the UI.
CREATE TABLE "scoring_state" (
    "id" INTEGER NOT NULL,
    "last_error" TEXT,
    "last_error_at" TIMESTAMP(3),

    CONSTRAINT "scoring_state_pkey" PRIMARY KEY ("id")
);
