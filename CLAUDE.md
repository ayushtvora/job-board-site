# Job Board Site

A personal tool that scrapes corporate career pages for job listings in specific
fields, stores them in Postgres, and displays them in a web table where each job
has a persistent "Applied?" checkbox — so I can track which jobs I've already
applied to without re-checking manually every time I revisit the site.

This is a single-user personal tool deployed on my own server. The app itself
has no login/auth logic — access is gated at the network layer by Cloudflare
Access in front of the deployment (see Deployment section).

## Architecture

Three containers, orchestrated with Docker Compose:

1. **web** — Next.js (TypeScript, App Router) app. Serves the UI (job table)
   and the API routes that read jobs / toggle "applied" state. Talks to Postgres
   directly (via Prisma).
2. **db** — PostgreSQL. Single source of truth for scraped jobs and applied state.
3. **scraper** — Python service (Playwright for JS-rendered career sites, plus
   BeautifulSoup/httpx for simpler static ones). Runs continuously with an
   internal scheduler (not host cron) that kicks off a scrape on an interval
   (e.g. daily). Writes directly to Postgres.

Rationale: Next.js keeps UI+API in one deployable unit (simple on a personal
server). Python was chosen for the scraper because of its scraping ecosystem
(Playwright/BeautifulSoup), and because scraping logic is naturally
per-company/isolated, so it doesn't need to share code with the web app.

## Database schema (planned)

```
companies
  slug          text PK          -- e.g. "rbc"
  name          text             -- e.g. "RBC"

jobs
  id            serial PK
  company_id    text FK -> companies.slug
  external_id   text             -- job ID/slug from the source site
  title         text
  url           text
  location      text
  category      text             -- e.g. "Technology, Analytics & Research"
  posted_date   date null        -- if the source site exposes it; null means
                                  -- it doesn't. The API/UI never show a blank
                                  -- date though — see "Posted date fallback"
                                  -- below.
  first_seen_at timestamptz      -- set on first insert
  last_seen_at  timestamptz      -- updated every time a scrape still finds it
  is_active     boolean          -- false once a scrape run no longer finds it
  applied       boolean default false
  applied_at    timestamptz null
  will_apply    boolean default true
  platform      text             -- ATS platform, e.g. "Workday", "Eightfold"
                                  -- set by the scraper, used as the link text
                                  -- in the UI instead of the raw URL

  unique (company_id, external_id)

scrape_runs
  id            serial PK
  company_id    text FK -> companies.slug
  started_at    timestamptz
  finished_at   timestamptz null   -- null while a run is in progress
  status        text               -- "success" | "error"
  error_message text null          -- set when status = "error"
```

Scraper behavior:
- Upsert on `(company_id, external_id)`. Never overwrite `applied`,
  `applied_at`, or `will_apply` on upsert — those are only ever changed by
  the web app.
- On each scrape run, for jobs not seen this run (i.e. `last_seen_at` wasn't
  updated):
  - If `applied = true`, keep the row but set `is_active = false` — preserves
    applied history even after the listing closes.
  - If `applied = false`, delete the row — no reason to keep a stale listing
    I never applied to.
- Each company gets its own scraper module (e.g. `scrapers/rbc.py`) implementing
  a shared interface (return a list of normalized job dicts); a runner loops
  over configured company scrapers. One company's scraper raising an error
  must not stop the runner from scraping the remaining companies — catch and
  isolate failures per company.
- If a source site doesn't expose a stable job ID, the scraper must make one
  up itself (e.g. a hash of title + location, or a slug derived from the job
  URL) rather than leaving `external_id` blank. It must be **deterministic**
  across runs for the same job — a random or run-dependent ID would break the
  `(company_id, external_id)` upsert match and create duplicate rows every
  scrape instead of updating `last_seen_at` on the existing one.
- `category` is free text straight from the source site — no normalization
  across companies is needed (a "Technology" category at one company doesn't
  need to line up with another's naming).
- Every run, per company, writes a `scrape_runs` row: `status = "success"` on
  a normal completion, or `status = "error"` with `error_message` set if the
  scraper raised. This is how the web app surfaces scrape failures (see
  Default view below) without the scraper and web app calling each other
  directly.

## Default view (UI)

The main table, in column order:

| Company | Job Title | Job ID | Link | Posted Date | Applied | Will Apply |
|---|---|---|---|---|---|---|

- **Job ID** is `jobs.external_id`.
- **Link** renders as a hyperlink to `jobs.url`, with link text set to
  `jobs.platform` (e.g. "Workday") instead of the raw URL.
- **Applied** and **Will Apply** render as checkboxes, editable inline; each
  edit fires the `PATCH /api/jobs/:id` call (see API contract below).
- **Posted date fallback**: when `posted_date` is null, the displayed date
  (and the `postedDate` field in the API response) falls back to
  `first_seen_at` instead — the date the job was first scraped is the best
  available proxy for when it was posted, so this column is never blank.
  `posted_date` itself in the database is untouched by this; the fallback is
  applied only where the value is displayed/returned.

Default sort: **effective** posted date descending (most recent first — using
the same `posted_date` / `first_seen_at` fallback as the displayed column, so
sort order always matches what's shown), then `company` ascending, then
`job_title` ascending.

Default filter (applied automatically, no user action needed): show only rows
where `is_active = true AND applied = false AND will_apply = true`. In other
words, the default view is "open listings I haven't applied to and still
intend to." Rows that fall out of this filter aren't deleted (unless the
delete-on-scrape rule above already removed them) — they just aren't shown
here.

"Show hidden jobs" toggle: a single UI control that, when on, also includes
rows that are hidden because they're expired (`is_active = false`) or already
applied to (`applied = true`) — i.e. it drops the `is_active`/`applied`
conditions from the filter but still respects `will_apply = true`. Jobs with
`will_apply = false` aren't considered "hidden" in this sense and stay out of
scope for now (a separate "show everything" view can cover those later if
needed).

Scrape error banner: the UI checks scrape status (see `GET /api/scrape-status`
below) and shows a dismissible popup/banner if any company's most recent
scrape run has `status = "error"`, naming the company so a broken scraper for
one company doesn't get missed just because others are still succeeding.

## API contract

Both routes live in the Next.js app (`web`), backed by Prisma.

**`GET /api/jobs`**
- Returns the job list, sorted by the default sort order above. Default query
  (no params) applies the default filter above and includes all default-view
  columns.
- `showHidden=true` drops the `is_active`/`applied` conditions from the
  filter (still respecting `will_apply = true`), per the "Show hidden jobs"
  toggle above.
- Optional query params (future-friendly, not required for v1):
  `company`, `is_active`, `applied`, `will_apply` to override the default
  filter further, e.g. for a later "show everything" view.
- Response: JSON array of jobs, each shaped like:
  ```json
  {
    "id": 123,
    "company": "RBC",
    "title": "Software Developer",
    "externalId": "R-00012345",
    "url": "https://jobs.rbc.com/...",
    "platform": "Workday",
    "postedDate": "2026-09-10",
    "applied": false,
    "willApply": true
  }
  ```
  `postedDate` is always a date string, never `null` — see the posted date
  fallback rule in the Default view section above.

**`PATCH /api/jobs/:id`**
- The *only* way `applied` and `will_apply` are ever modified — enforces the
  "scraper never touches these" rule from the schema section.
- Body: `{ "applied"?: boolean, "willApply"?: boolean }` — only these two
  fields are accepted; any other field in the body is rejected (400).
- When `applied` transitions to `true`, the server sets `applied_at = now()`;
  when it transitions back to `false`, `applied_at` is cleared to `null`.
- Returns the updated job row (same shape as above). 404 if `id` doesn't exist.

**`GET /api/scrape-status`**
- Returns the most recent `scrape_runs` row per company, so the UI can show
  the error banner described in the Default view section.
- Response: JSON array shaped like:
  ```json
  [
    {
      "company": "RBC",
      "status": "error",
      "errorMessage": "Timed out waiting for job list to render",
      "finishedAt": "2026-09-17T06:03:12-04:00"
    }
  ]
  ```
- Polled by the UI on page load (and optionally on an interval) rather than
  pushed — keeps web and scraper decoupled through Postgres only.

## Scrape schedule

Each configured site is scraped once per day at **6:00 AM** (server-local
time — set the `TZ` env var explicitly on the scraper container so "6am"
doesn't silently mean UTC). Handled by the scraper's own internal scheduler,
not host cron (per the architecture decision above).

## Current scope

- Only company/source configured so far: **RBC**, Technology/Analytics/Research
  jobs — https://jobs.rbc.com/ca/en/c/technology-analytics-research-jobs
- More companies and filters will be added later; scraper architecture should
  make adding a new company a matter of adding a new scraper module + a
  `companies` row, not restructuring shared code.

### RBC scraping approach (investigated 2026-09-17)

RBC's careers site runs on Phenom People's Career Site Builder — looks
JS-heavy, but the job data for each page of results is actually embedded
directly in the server-rendered HTML, so **no browser/Playwright is needed
for RBC**: a plain HTTP GET (`httpx`) is enough. Confirmed with plain `curl`
(no special headers, cookies, or session) — no bot-blocking encountered.

- Each category/search page embeds a `<script>var phApp = phApp || {...}`
  blob containing a JSON object; the job listings live in there. Extract by
  locating that blob and parsing it as JSON (don't regex the fields
  individually — the blob is one JSON object, so parse it once).
- **Pagination**: append `?from=<offset>&s=1` to the URL, `offset` in steps
  of 10 (10 jobs embedded per page) — e.g. `...jobs?from=10&s=1` for the
  second page. Keep incrementing until a page returns no new job IDs.
  Query params like `start=` (a natural first guess) are silently ignored —
  `from` is the real one, found by watching the network request an actual
  "Next" click fires in a real browser.
  - The default sort ("most relevant") isn't fully stable across requests —
    consecutive pages can overlap slightly. Doesn't matter functionally
    (the upsert on `(company_id, external_id)` makes re-seeing a job a
    no-op), but prefer a "most recent" sort param if/when reused for other
    categories, to minimize redundant fetches.
- **Fields available per job** (confirmed from the embedded blob):
  `jobId` (e.g. `"R-0000170843"` — use as `external_id`), `title`,
  `postedDate` (ISO datetime, e.g. `"2026-08-12T00:00:00.000+0000"` — take
  the date part), `category`, `location` / `cityStateCountry`, and
  `applyUrl` — the real application link, which points at
  `*.wd3.myworkdayjobs.com` for every job seen. **`platform` = `"Workday"`**
  for RBC (answers the open question below).

## Deployment

- GitHub Actions runs on a **self-hosted runner installed on my personal
  server** (no SSH secrets needed). The workflow (`.github/workflows/deploy.yml`)
  runs on push to `main`: `docker compose build`, then
  `docker compose run --rm web npx prisma migrate deploy` (run *inside* the
  freshly-built `web` image, not on the bare host — the server has no Node.js
  installed, everything else on it is Docker containers, so migrations stay
  containerized too rather than installing Node just for this), then
  `docker compose up -d`.
- The checkout step disables `actions/checkout`'s default clean
  (`git clean -ffdx`) — that would otherwise delete the production `.env`
  (gitignored, sitting in this same checked-out directory) on every run after
  the first.
- `docker-compose.yml` defines all three services plus a named volume for
  Postgres data.
- Env vars (DB credentials, connection strings) via `.env` on the server, not
  committed to the repo.
- Access control: **Cloudflare Access** sits in front of the deployed `web`
  service (via a Cloudflare Tunnel or equivalent), restricting access to my
  own identity. The Next.js app itself implements no auth — it trusts that
  anything reaching it has already been authenticated by Cloudflare. This
  only applies to the deployed instance; local dev has no such gate.

## Local dev workflow

- `docker compose up --build` runs all three services locally (web, db,
  scraper) against a local Postgres volume — same compose file as production,
  just pointed at `.env.local` instead of the server's `.env`.
- For faster iteration on the web app, run Postgres in Docker
  (`docker compose up db`) but run Next.js on the host with `npm run dev`,
  pointed at that local Postgres via `DATABASE_URL`.
- Prisma migrations: `npx prisma migrate dev` to create/apply a migration
  locally and update the client; `npx prisma studio` to browse/edit data by
  hand during development.
- Seed data: a seed script (`prisma/seed.ts` or similar) inserts a handful of
  fake companies/jobs, so the UI can be built and tested without repeatedly
  hitting RBC's real site.
- Scraper dev runs: the scraper entrypoint should support a `--once` flag (or
  equivalent) to run a single scrape immediately on demand, instead of
  waiting for the 6am schedule — needed for testing scraper changes locally.

## Environment variables

| Variable | Used by | Purpose |
|---|---|---|
| `DATABASE_URL` | web, scraper | Postgres connection string; must be consistent across both. |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | db | Initializes the Postgres container; `DATABASE_URL` is built from these. |
| `TZ` | scraper | Explicit timezone (e.g. `America/Toronto`) so the 6am schedule means local time, not UTC. |
| `NODE_ENV` | web | `development` locally, `production` on the server. |

- Local values go in a gitignored `.env.local` (or `.env` used only by
  `docker compose` locally); production values live in `.env` on the
  personal server, per the Deployment section — neither is committed.

## Conventions

- Language: TypeScript for web app, Python for scraper.
- ORM: Prisma (web app reads/writes Postgres, including migrations).
- Keep scraper and web app decoupled — they only interact through Postgres,
  never call each other directly.

## Open questions / next steps

- [x] Investigate RBC's careers site structure — see "RBC scraping approach"
      under Current scope above.
- [x] Scaffold Next.js app, Prisma schema, docker-compose.yml.
- [x] Set up self-hosted GitHub Actions runner on the personal server —
      installed as a systemd service (`~/actions-runner`), verified with two
      real deploys end-to-end (including catching and fixing a real bug in
      the scraper's scheduler startup). The app is up on the server at
      `localhost:3001` there (host port 3001 → container port 3000 — 3000
      was already taken by something else on the server); it isn't
      reachable at a public URL yet — that's
      the Cloudflare Tunnel/Access item below.
- [x] Confirm RBC's ATS platform name to populate `jobs.platform` — Workday.
- [x] Set up Cloudflare Tunnel public hostname for the deployed `web` service
      — live at `jobs.ayushtvora.com` (routed to `localhost:3001` via the
      existing host-networked `cloudflared` container on the server).
- [ ] **Set up Cloudflare Access in front of `jobs.ayushtvora.com`** — the
      hostname above is reachable by anyone right now, not just me; this is
      the auth gate the top of this file assumes is already in place. Plan:
      add a Google login method in Zero Trust (needs an OAuth client from
      Google Cloud Console) and an Access application policy restricting to
      my own email. Deferred for now, not urgent but shouldn't stay open long
      since the job data is otherwise public.
- [ ] Decide the exact deterministic external-ID scheme for sites without a
      stable job ID (e.g. hash of title+location vs. slug from the URL) —
      not needed for RBC, which exposes a stable `jobId`, but still open for
      future companies that might not.
- [x] Build the RBC scraper module (`scrapers/rbc.py`) using the approach
      above, wire it into the runner + scheduler, and write the
      `scrape_runs` row per CLAUDE.md's scraper behavior section — verified
      end-to-end against the live site and local Postgres (see git history).
