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

- Companies/sources configured so far:
  - **RBC**, Technology/Analytics/Research jobs —
    https://jobs.rbc.com/ca/en/c/technology-analytics-research-jobs
  - **SOTI**, Mississauga HQ / Product Development jobs —
    https://soti.wd3.myworkdayjobs.com/Careers/jobs?locations=023f9d25c4c11000bbfc52f5b4120000&EEB_-_Job_Categories_for_External_Site_Extended=267bdbcbbd671001697698c0843a0001
  - **EA**, Canada / Software Development jobs — https://jobs.ea.com/en_US/careers
  - **BMO**, Canada / Technology jobs — https://jobs.bmo.com/ca/en/search-results
  - **CIBC**, Canada / Information Technology jobs —
    https://cibc.wd3.myworkdayjobs.com/search?jobFamilyGroup=4bbe6c74e8a70126f29430a881012510&Country=a30a87ed25634629aa6c3958aa2b91ea
  - **TD**, Canada / Technology Solutions jobs —
    https://td.wd3.myworkdayjobs.com/en-US/TD_Bank_Careers?jobFamilyGroup=de769652963501f2001247b507040dac&locationCountry=a30a87ed25634629aa6c3958aa2b91ea
  - **Scotiabank**, IT & Digital Banking Jobs (no separate country filter) —
    https://jobs.scotiabank.com/go/IT-&-Digital-Banking-Jobs/2298017/
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

### SOTI scraping approach (investigated 2026-09-18)

SOTI's careers site runs on Workday directly (`*.wd3.myworkdayjobs.com`) —
unlike RBC's Phenom People site, so this isn't the same scraping approach,
just the same downstream ATS. Workday exposes an undocumented but stable
JSON API (`/wday/cxs/...`, "CXS" = Workday's candidate experience API) — no
Playwright needed, plain HTTP calls with `httpx` are enough.

- **List endpoint**: `POST https://soti.wd3.myworkdayjobs.com/wday/cxs/soti/Careers/jobs`
  with a JSON body `{"appliedFacets": {...}, "limit": N, "offset": N, "searchText": ""}`.
  `appliedFacets` keys are Workday facet parameter names (e.g. `locations`,
  `EEB_-_Job_Categories_for_External_Site_Extended`); values are lists of
  opaque facet IDs — the same IDs that appear as query params on the site's
  own filtered URL (confirmed the two IDs in this scrape's URL resolve to
  "Mississauga, Canada – Meadowvale Office (HQ)" and "Product Development"
  respectively, via the facet metadata returned by the same endpoint called
  with an empty `appliedFacets`).
- **Pagination**: `limit`/`offset` in the request body, in contrast to RBC's
  query-string pagination. Increment `offset` by `limit` until it reaches
  the response's `total`.
- **Fields available per job** from the list response: `title`,
  `externalPath` (relative job URL), `locationsText`, `bulletFields[0]` (the
  job requisition ID, e.g. `"R09972"` — use as `external_id`), and
  `postedOn` — a relative string ("Posted 18 Days Ago"), **not** a usable
  date.
- **No per-job category or exact date** in the list response — unlike RBC's
  embedded blob. Since this scraper's `appliedFacets` are fixed to one
  category, `category` is hardcoded to that facet's label rather than read
  per job.
- **Exact posted date + canonical apply URL**: fetch each job's detail page,
  `GET https://soti.wd3.myworkdayjobs.com/wday/cxs/soti/Careers<externalPath>`.
  Its `jobPostingInfo.startDate` is a plain ISO date (e.g. `"2026-08-31"`) —
  confirmed this lines up exactly with the list's relative "Posted N Days
  Ago" text (N days before the date this was checked). `jobPostingInfo.externalUrl`
  is the canonical apply URL (same domain, no separate ATS redirect — unlike
  RBC, SOTI's own careers site *is* the Workday instance). `jobReqId` there
  matches `bulletFields[0]` from the list response. **`platform` =
  `"Workday"`** for SOTI.
- This means one extra HTTP request per job per run (~12 jobs currently for
  this filter combination) — acceptable at this volume and cadence
  (once/day).

### EA scraping approach (investigated 2026-09-18)

EA's careers site (`jobs.ea.com`) runs on Avature, a third ATS distinct from
both RBC's (Phenom) and SOTI's (Workday). Unlike either of those, job data
isn't embedded as one parseable JSON blob — this is a plain server-rendered
HTML listing, so it's parsed with BeautifulSoup (`bs4`, added to
`requirements.txt`) instead.

- The filter form's "Country" and "Job Category" fields are Avature
  "dataset" fields backed by an autocomplete API — their option values are
  opaque numeric IDs not present anywhere in the static HTML (they're
  fetched as you type). Found these by driving the real filter UI with
  Playwright (installed temporarily for this investigation, not added to
  `requirements.txt` since the scraper itself doesn't need a browser) and
  capturing the request the filter form fires on submit:
  `8171=10577` is Country=Canada, `4536=8301` is Job Category=Software
  Development.
- The resulting listing URL is a plain GET, no session/cookies required:
  `https://jobs.ea.com/en_US/careers/Home/?8171=[10577]&8171_format=5683&4536=[8301]&4536_format=3019&listFilterMode=1`.
  The `_format` values are fixed companions to each field, not independently
  meaningful. **Pagination**: `jobOffset`, in steps of 20 — the site
  hard-caps the actual page size at 20 regardless of what `jobRecordsPerPage`
  requests (tried up to 200, still got 20 back).
- **Fields available per job** from the listing: title + detail URL
  (`.article__header__text__title a`), primary location
  (`.list-item-location`), and a numeric role ID that appears both as the
  URL's trailing path segment and as `.list-item-id` ("Role ID <n>") — used
  as `external_id`.
- **No per-job category or posted date** anywhere in the listing or detail
  page (checked both). Since this scraper's query is fixed to one category,
  `category` is hardcoded to that facet's label, same reasoning as SOTI.
- **Posted date**: EA also publishes an RSS feed at the same path
  (`Home/feed/`) that accepts the identical filter params and includes a
  real `pubDate` per job — but confirmed it always returns only its 20
  *most-recently-posted* matches for the given filter, completely ignoring
  `jobRecordsPerPage`/`jobOffset` (tried several values, got the same 20
  items back every time, in a different order/set than the default listing
  sort). So it's a partial, best-effort source: the scraper builds an
  `external_id -> pubDate` lookup from it once per run, and jobs outside
  that newest-20 slice just get `posted_date = None` — which is the
  sanctioned behavior per the posted-date-fallback rule (UI falls back to
  `first_seen_at`), not a workaround.
- **`platform` = `"Avature"`** for EA.

### BMO, CIBC, TD, Scotiabank scraping approach (investigated 2026-09-18)

Added four more companies in one pass, each landing on a platform already
covered by an existing scraper except Scotiabank:

- **BMO** (`scrapers/bmo.py`) — Phenom People, same as RBC (`phApp.ddo`
  blob). Two differences from RBC's scraper:
  - BMO's `/ca/en/` site section is Canada-only already (its own `country`
    facet reports 100% "Canada"), so "Country: Canada" needs no explicit
    filter.
  - Category filtering is a plain human-readable query param,
    `?category=Technology` (matches the facet label exactly, confirmed by
    the totalHits dropping to that facet's own count) — no opaque ID, unlike
    Workday. **Pagination quirk**: combining RBC's `&s=1` param with
    `category=...` here silently drops the category filter back to the
    unfiltered full set. Omitting `s` and paginating with `from=N` alone
    works correctly with the filter applied — confirmed via distinct,
    correctly-categorized jobs on later pages. `platform = "Workday"`,
    same as RBC (BMO's `applyUrl` also points at `*.wd3.myworkdayjobs.com`).
- **CIBC** (`scrapers/cibc.py`) and **TD** (`scrapers/td.py`) — Workday, same
  approach as SOTI. Facet parameter names differ per tenant (CIBC:
  `jobFamilyGroup` + `Country`; TD: `jobFamilyGroup` + `locationCountry`,
  the latter nested under a `locationMainGroup` facet group) but were
  confirmed against each site's own facet metadata, same as SOTI's. Notably,
  the Canada country-facet ID (`a30a87ed25634629aa6c3958aa2b91ea`) is
  identical across SOTI, CIBC, and TD — Workday appears to reuse common
  reference IDs (at least for countries) across independent tenants, though
  each tenant still needs its own facet *parameter name* confirmed
  separately.
  - TD's `bulletFields` includes a second element beyond the requisition ID
    — its "Job Family" (a finer sub-category under "Job Category", e.g.
    "Engineering", confirmed against TD's own `jobFamily` facet values). Used
    directly as `category` instead of hardcoding "Technology Solutions",
    since it's real per-job data. CIBC has no such second field, so its
    scraper hardcodes "Information Technology" like SOTI does.
  - **Bug found and fixed while building these**: the original SOTI/CIBC/TD
    scrapers re-read `total` from every page's response to decide when to
    stop paginating. TD's API reports `total: 0` on every page after the
    first (confirmed directly), which made `offset >= total` trip
    immediately and silently truncated results to just the first two pages
    (40 of TD's 95 matching jobs). Fixed in all three Workday scrapers to
    only trust `total` from the first page's response.
- **Scotiabank** (`scrapers/scotiabank.py`) — a fourth ATS platform: SAP
  SuccessFactors (Jobs2Web career site layer). Plain server-rendered HTML
  table, no session/JS needed, parsed with BeautifulSoup.
  - The given URL (`/go/IT-&-Digital-Banking-Jobs/2298017/`) is itself the
    category-specific landing page (Scotiabank's own "Technology" filter,
    per the request) — not a generic search with query-string facets. Only
    "Technology" was requested for Scotiabank, with no separate country
    filter (unlike BMO/CIBC/TD), so the scraper takes this page as-is,
    whatever countries happen to be in it.
  - **Pagination** is a URL *path segment*, not a query param, in steps of
    the page size (25): `.../2298017/0/`, `.../2298017/25/`, etc. — `/0/` is
    confirmed equivalent to the bare category URL (both report "Page 1"),
    so the scraper always includes the offset segment uniformly.
  - No per-job category is shown (the whole page is one category already),
    so `category` is hardcoded to the page's own label ("IT & Digital
    Banking Jobs"), same reasoning as the Workday scrapers.
  - Posted date is a plain human-readable string per row (e.g. "Sep 18,
    2026"), parsed directly — no RSS-style partial-coverage workaround
    needed here, unlike EA.
  - **`platform` = `"SuccessFactors"`** for Scotiabank.

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
- [x] Set up Cloudflare Access in front of `jobs.ayushtvora.com` — verified
      the hostname now 302-redirects to the Cloudflare Access login page
      instead of serving the app directly.
- [ ] Decide the exact deterministic external-ID scheme for sites without a
      stable job ID (e.g. hash of title+location vs. slug from the URL) —
      not needed for RBC, which exposes a stable `jobId`, but still open for
      future companies that might not.
- [x] Build the RBC scraper module (`scrapers/rbc.py`) using the approach
      above, wire it into the runner + scheduler, and write the
      `scrape_runs` row per CLAUDE.md's scraper behavior section — verified
      end-to-end against the live site and local Postgres (see git history).
