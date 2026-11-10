-- Scoring queue order (see CLAUDE.md "Job descriptions and relevance
-- score"): a cheap local estimate of how well each job fits the resume,
-- computed by the web app's scoring worker so the jobs most likely to
-- score high are sent to the model first. priority_key records the
-- resume and heuristic version it was computed with.
ALTER TABLE "jobs" ADD COLUMN "score_priority" DOUBLE PRECISION;
ALTER TABLE "jobs" ADD COLUMN "priority_key" TEXT;
