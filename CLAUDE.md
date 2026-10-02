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
  - **Manulife**, Canada / Information Technology jobs — scraped from their
    Workday tenant (`manulife.wd3.myworkdayjobs.com/MFCJH_Jobs`) rather than
    the requested careers.manulife.com page, which is WAF-blocked; see
    "Manulife scraping approach" below.
  - **Liberty Mutual**, Canada / Technology jobs — investigated, platform
    confirmed (Eightfold), but currently has **zero** Canada postings; see
    "Liberty Mutual scraping approach" below.
  - **Blizzard**, Canada / Engineering & Technology jobs — investigated,
    platform confirmed, but currently has **zero** Canada postings; see
    "Blizzard scraping approach" below.
  - **Riot Games**, Canada / Engineering jobs — investigated, platform
    confirmed (Greenhouse), but currently has **zero** Canada postings; see
    "Riot Games scraping approach" below.
  - **Nvidia**, Canada / Engineering jobs (Workday `jobFamilyGroup`) —
    https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite — see
    "Nvidia scraping approach" below.
  - **UBC**, Canada (Vancouver/Okanagan campuses) / M&P Information Systems &
    Tech jobs (Workday `jobFamily`) —
    https://ubc.wd10.myworkdayjobs.com/ubcstaffjobs — see "UBC scraping
    approach" below.
  - **Reddit**, Canada / Engineering department jobs (Greenhouse) —
    https://job-boards.greenhouse.io/reddit — see "Reddit scraping approach"
    below.
  - **ATS Corporation** (atsautomation.com), Canada / Engineering jobs —
    scraped from its SuccessFactors Jobs2Web site `jobs.atsautomation.com`
    (unblocked 2026-09-25); see "ATS Corporation and Eclipse Automation,
    unblocked" below. (The original 2026-09-19 notes further down describe
    the dead end that came before.)
  - **Intel**, Canada / Software Engineering jobs (Workday `jobFamilyGroup`)
    — https://intel.wd1.myworkdayjobs.com/External — see "Intel scraping
    approach" below.
  - **Oracle**, Canada / Product and Research jobs (Oracle Recruiting Cloud)
    — https://careers.oracle.com/en/sites/jobsearch — see "Oracle scraping
    approach" below.
  - **Spotify**, Canada / Engineering jobs (Lever) —
    https://jobs.lever.co/spotify — see "Spotify scraping approach" below.
  - **Adobe**, Canada / Engineering and Product jobs (Workday apply backend
    via Phenom front-end) — https://careers.adobe.com/us/en/search-results —
    see "Adobe scraping approach" below.
  - **Sony**, Canada / Product Development – Software jobs (Workday, via
    sonyjobs.com's embedded Workday iframe) —
    https://sonyglobal.wd1.myworkdayjobs.com/SonyGlobalCareers — see "Sony
    scraping approach" below.
  - **AMD** — investigation blocked, not scraper-ready: iCIMS backend
    returns an AWS WAF captcha challenge to every automated request; see
    "AMD scraping approach" below.
  - **Uber** — investigation blocked, not scraper-ready: custom in-house
    app with an app-level CSRF gate on its job search API; see "Uber
    scraping approach" below.
  - **Airbnb**, Canada / Software Engineering jobs (Greenhouse) —
    https://boards-api.greenhouse.io/v1/boards/airbnb — see "Airbnb, Databricks,
    Stripe scraping approach" below. Currently 0 jobs match Canada +
    Software Engineering simultaneously.
  - **Databricks**, Canada / Engineering jobs (Greenhouse) —
    https://boards-api.greenhouse.io/v1/boards/databricks — see "Airbnb,
    Databricks, Stripe scraping approach" below.
  - **Stripe**, Canada / Engineering jobs (Greenhouse, heuristic dept match)
    — https://boards-api.greenhouse.io/v1/boards/stripe — see "Airbnb,
    Databricks, Stripe scraping approach" below.
  - **SAP**, Canada / Software-Design and Development jobs (SAP
    SuccessFactors XML feed + SmartRecruiters; jobs.sap.com was rebuilt
    2026-10-02) — see "SAP scraping approach" below.
  - **Snowflake**, Canada / Engineering jobs (Phenom front-end, Ashby is the
    real ATS) — https://careers.snowflake.com/us/en/search-results?category=Engineering
    — see "Snowflake scraping approach" below.
  - **Metrolinx**, Canada (all jobs are Canada already) / IT-adjacent roles
    (Oracle Fusion Cloud Recruiting) —
    https://www.metrolinx.com/en/about-us/careers — see "Metrolinx scraping
    approach" below.
  - **Eclipse Automation**, Canada / software & engineering roles
    (Dayforce) — unblocked 2026-09-25 once Dayforce's maintenance ended;
    see "ATS Corporation and Eclipse Automation, unblocked" below.
  - **Meta** — investigated; scrapable in principle but would require a
    full Playwright browser session on every scrape run (not lightweight
    HTTP like every other company here) because its GraphQL API requires
    per-session anti-automation tokens; not yet built. See "Meta scraping
    approach" below.
  - **Amazon**, Canada / Software Development jobs (custom in-house JSON
    API) — https://www.amazon.jobs/en/search.json — see "Amazon scraping
    approach" below.
  - **Google**, Canada / Software Engineer jobs (custom in-house,
    server-rendered, free-text relevance search) —
    https://www.google.com/about/careers/applications/jobs/results — see
    "Google scraping approach" below.
  - **Apple**, Canada / Software and Services team jobs (custom in-house) —
    https://jobs.apple.com/en-us/search?location=canada-CANC — see "Apple
    scraping approach" below.
  - **Microsoft**, Canada / Software Engineering department jobs
    (Eightfold) — https://apply.careers.microsoft.com — see "Microsoft
    scraping approach" below.
  - **IBM**, Canada / Software Engineering jobs (IBM's own Elasticsearch
    search index; Avature is the underlying application system) —
    https://www.ibm.com/careers/search — see "IBM scraping approach" below.
  - **Canonical**, Canada-adjacent / Engineering jobs (Greenhouse; see
    caveats on Canada and category matching below) —
    https://boards-api.greenhouse.io/v1/boards/canonical — see "Canonical
    scraping approach" below.
  - **Shopify**, Canada/Americas-remote / Engineering jobs (Ashby data via
    the careers page's React Router loader) — https://www.shopify.com/careers
    — see "Shopify, Thomson Reuters, Salesforce, Autodesk, Sun Life scraping
    approach" below.
  - **Thomson Reuters**, Canada / Technology Careers jobs (Workday) —
    https://thomsonreuters.wd5.myworkdayjobs.com/External_Career_Site
  - **Salesforce**, Canada / Software Engineering jobs (Workday) —
    https://salesforce.wd12.myworkdayjobs.com/External_Career_Site
  - **Sun Life**, Canada / IT jobs (Workday) —
    https://sunlife.wd3.myworkdayjobs.com/Experienced-Jobs
  - **Autodesk**, Canada / Development Engineering + Technology jobs
    (Eightfold) — https://jobs.autodesk.com/careers — see "Autodesk" under
    "ATS Corporation and Eclipse Automation, unblocked" below.
  - Fourth wave, batches 2–6 (all Canada-scoped, tech/engineering
    categories; see "Fourth wave, batches 2–6 scraping approach" below for
    per-company details): **Cohere** (Ashby), **Wealthsimple** (Ashby),
    **Faire** (Greenhouse), **Cloudflare** (Greenhouse), **Dropbox**
    (Greenhouse), **Pinterest** (Greenhouse), **Instacart** (Greenhouse),
    **Coinbase** (Greenhouse), **National Bank** (Avature), **Intact**
    (Workday), **Canada Life** (SuccessFactors Jobs2Web), **Questrade**
    (Dayforce), **Interac** (Workday), **Rogers** (SuccessFactors
    Jobs2Web), **Bell** (Phenom → SuccessFactors), **TELUS**
    (SuccessFactors Jobs2Web — currently zero tech postings), **Ubisoft**
    (SmartRecruiters), **Clio** (Workday), **1Password** (Ashby),
    **Kinaxis** (iCIMS via Jibe), **OpenText** (Phenom → SuccessFactors),
    **Geotab** (Greenhouse), **D2L** (Greenhouse), **Arctic Wolf**
    (Workday), **Workday** (Workday).
  - Fifth wave (all Canada-scoped, tech/engineering categories; see "Fifth
    wave scraping approach" below):
    - Greenhouse: **Ada**, **League**, **Tenstorrent**, **DoorDash**,
      **Lyft**, **Okta**, **Asana**, **Samsara**, **Twilio**, **Affirm**,
      **Figma**, **Datadog**.
    - Ashby: **Jobber**, **Neo Financial**, **KOHO**, **Benevity**,
      **Hopper**, **Loopio**, **Thinkific**.
    - Lever: **Waabi**, **EQ Bank**.
    - Workday: **Cisco**, **Ciena**, **PayPal**, **Mastercard**, **CPP
      Investments**, **OMERS**, **Ontario Teachers'**, **Desjardins**,
      **Loblaw Digital**, **Canadian Tire**, **CAE**, **ApplyBoard**,
      **BlackBerry** (+ QNX), **Cadence**.
    - Eightfold: **Qualcomm**, **Ericsson**, **ATB Financial**.
    - Oracle Recruiting Cloud: **Nokia**, **Definity**, **Fortinet**.
    - Phenom → Taleo: **Air Canada**.
    - SuccessFactors Jobs2Web: **Celestica**, **Hydro One**, **City of
      Toronto**, **Bank of Canada**.
    - SmartRecruiters: **Arista Networks**.
    - TalentBrew → Avature: **Intuit**, **Synopsys**.
    - Other: **Xanadu** (HiBob), **Vidyard** (Kula), **FreshBooks** (Gem).
  - Investigated but **not scraper-ready**: **CGI**, **Ontario Public
    Service**, **Tesla**, **CN**, **Siemens**. See "Fifth wave scraping
    approach" below.
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

### Manulife scraping approach (investigated 2026-09-19)

**careers.manulife.com is unscrapeable — don't retry it without new
information.** It's a Phenom People front-end (same `/{locale}/c/<category>-jobs`
URL shape as RBC), but Akamai returns an immediate 403 "Access Denied" block
page to every automated client tried: plain HTTP, full browser-like headers,
and a real headless Chromium — from three different networks, including the
personal server this scraper actually runs from. Every path on the domain is
blocked, including the site root and `manulife.com` itself. It's a flat WAF
block, not a JS challenge, so there's no challenge for a scraper to solve and
no amount of header/browser tuning helps.

Instead, `scrapers/manulife.py` scrapes **Manulife's Workday tenant
directly** — Workday is the system of record behind that Phenom front-end
(as it is for RBC and BMO, whose apply links also point at Workday), and its
API isn't behind the WAF.

- Tenant/site: `manulife.wd3.myworkdayjobs.com/MFCJH_Jobs` — a combined
  Manulife/John Hancock careers site. The site ID is not guessable (a dozen
  plausible names all 404'd); it was found from a real apply link to this
  tenant published on a third-party job aggregator.
- Facet parameters are `jobFamilyGroup` and `Location_Country`, confirmed
  against the tenant's own facet metadata: `838ae04677e543c2a0a85dfd1cab030a`
  = "Information Technology Group" (33 Canadian jobs), and the usual shared
  `a30a87ed25634629aa6c3958aa2b91ea` = "Canada".
- **Caveat on the category mapping**: because the Phenom site is unreachable,
  there's no way to verify that its "technology-jobs" category contains
  exactly the same jobs as Workday's "Information Technology Group". It's the
  obvious direct match, but adjacent Workday groups exist that a "technology"
  bucket *might* also include — most plausibly "Advanced Analytics - AI
  Group" (10 Canadian jobs). Adding it would be a one-line change to
  `CATEGORY_FACET_ID`'s list in the scraper if that's ever wanted.
- `bulletFields` is `[reqId, city]` here (the second element is a location,
  not a category like TD's), so `category` is hardcoded to the facet label.
- **Location comes from the detail endpoint**, unlike the other Workday
  scrapers: Manulife has many multi-location postings whose listing
  `locationsText` is just a placeholder like "2 Locations" / "50 Locations",
  while the detail endpoint's `location` is always a real place name.

### Liberty Mutual, Blizzard, Riot Games, Nvidia, UBC, Reddit, ATS Corporation scraping approach (investigated 2026-09-19)

Batch investigation for a second wave of companies. Three of these
(Liberty Mutual, Blizzard, Riot Games) have their platform/API fully
confirmed but currently have **zero** Canada job postings — not a scraping
failure, confirmed by testing the filter against a known-populated value
(Liberty Mutual) or the full unfiltered facet aggregation (Blizzard, Riot).
Scraper modules for these should still be written per CLAUDE.md's shared
interface, they'll just return an empty list most of the time until Canada
roles open up.

- **Liberty Mutual** — real URL `https://searchjobs.libertymutualgroup.com/careers`.
  Platform: **Eightfold** (confirmed via `X-EF-NS`/`X-EF-CID` response headers,
  `/gen/js/ef-*.js` assets). Public JSON API:
  `GET https://searchjobs.libertymutualgroup.com/api/apply/v2/jobs?domain=libertymutual.com&start=0&num=<N>&query=`
  — note `domain` must be `libertymutual.com`, not `libertymutualgroup.com`
  (the latter silently returns a generic 404-shell). Pagination: `start`/`num`
  query params. Filtering: `location=` and `department=` query params are
  real and confirmed working (`location=Boston, Massachusetts, United States`
  → 120 results; `location=Canada` → 0; `department=Technology&location=Canada`
  → 0). Fields per job (`positions[]`): `display_job_id` (e.g.
  `"2026-261897"`, matches the site's visible req-ID format — use as
  `external_id`), `name`, `location`/`locations[]`, `department`,
  `canonicalPositionUrl`, `t_create` (real Unix timestamp, genuine posted
  date, not relative text). `platform` = **`"Eightfold"`**.
- **Blizzard** — real URL `https://careers.blizzard.com/global/en`, still a
  standalone site (not folded into Microsoft's careers portal). Platform:
  **Phenom People** front-end (same `phApp.ddo` blob pattern as RBC/BMO), but
  every job's `applyUrl` points at
  `xboxgaming.wd1.myworkdayjobs.com/Blizzard_External_Careers/...` — i.e. the
  real ATS behind it is Microsoft's Xbox Gaming Workday tenant, post-acquisition
  (same reasoning as Manulife: record the real backend, not the Phenom shell).
  Category page: `https://careers.blizzard.com/global/en/engineering-technology`
  → search results via `rk=l-engineering-technology` (confirmed real category
  refinement param; the facet in the returned blob showed `{"Engineering":9}`
  exclusively when applied). Pagination: `from=N` in steps of 10, same
  "most-relevant sort isn't fully stable" caveat as RBC. **No server-side
  Canada filter could be confirmed** — the `country` facet across all 47 open
  roles sitewide is US/China/Ireland only right now, so there's no live
  Canadian job to reverse-engineer a filter param from. Given the low volume
  (9 jobs in this category), the scraper should fetch the category's full
  unfiltered result set and filter `country === "Canada"` client-side in
  Python, rather than relying on an unconfirmed facet param. Fields: same
  blob shape as RBC (`jobId`, `title`, `postedDate`, `category`,
  `location`/`cityStateCountry`, `country`, `applyUrl`). `platform` =
  **`"Workday"`** (per the applyUrl convention established for RBC/BMO).
- **Riot Games** — real URL `https://www.riotgames.com/en/work-with-us`, a
  genuinely custom-built React site, but job detail pages embed the standard
  Greenhouse widget (`<div id="grnhse_app">`, board token `riotgames`), so
  the canonical data source is Greenhouse's public API:
  `GET https://boards-api.greenhouse.io/v1/boards/riotgames/jobs?content=true`
  (155 jobs, one call, no pagination needed). Greenhouse's public boards API
  has **no server-side location filter** (`location=` query param is
  ignored — confirmed by diffing filtered vs. unfiltered responses); Canada
  jobs must be found by client-side filtering `location.name`. Currently **0**
  Canada jobs (matches the site's own location dropdown, which has no
  Canada option right now). Category facet: each job's `metadata[]` array
  has a `"Craft"` field with confirmed values including `"Software
  Engineering Group"`, `"Engineering"`, `"Infrastructure"`, `"QA Group"`,
  `"Data"`. Fields: `id` (stable numeric, use as `external_id`),
  `requisition_id` (e.g. `"REQ-0010050"`), `title`, `absolute_url`,
  `location.name`, `departments[]`, `offices[]`, `metadata[]`,
  `first_published` (real ISO datetime, distinct from `updated_at`).
  `platform` = **`"Greenhouse"`**.
- **Nvidia** — tenant `nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite`,
  Workday CXS API at `.../wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs`.
  Category facet `jobFamilyGroup`, Engineering =
  `0c40f6bd1d8f10ae43ffaefd46dc7e78`. Country is **not** a flat facet like
  other tenants — nested under `locationHierarchy1` (under a
  `locationMainGroup`), Canada = `2fcb99c455831013ea529c3b93ba3236` — a
  tenant-specific ID, *not* the shared `a30a87ed25634629aa6c3958aa2b91ea` used
  by SOTI/CIBC/TD/Manulife, reconfirming that every tenant's facet IDs need
  independent verification. Combined query
  (`appliedFacets: {"jobFamilyGroup":[...], "locationHierarchy1":[...]}`)
  confirmed working: **10 real Canada + Engineering jobs**. Pagination:
  `limit`/`offset` in the POST body; trust `total` only from the first page
  (per the existing TD bug fix). `bulletFields` is single-element here
  (`[reqId]`, no second field like TD/Manulife). Detail endpoint confirmed
  at `.../wday/cxs/nvidia/NVIDIAExternalCareerSite<externalPath>` for real
  `startDate`/`location`/`externalUrl`. `platform` = **`"Workday"`**.
- **UBC** — three separate Workday sites by employee type; staff jobs are
  the relevant one: `ubc.wd10.myworkdayjobs.com/ubcstaffjobs`, CXS API at
  `.../wday/cxs/ubc/ubcstaffjobs/jobs`. No country filter needed — every
  location facet value is already a BC campus. Category facet is
  `jobFamily`, fine-grained by union/role rather than a broad tech bucket;
  closest Software-Engineering equivalent, confirmed against actual returned
  job titles ("Programmer Systems Analyst II", "Support Analyst I", "Network
  Analyst I, Wireless"): **`"M&P Information Systems & Tech"` =
  `0f50d6e300ee011d7120b51e4001a9f9`** (4 jobs). Detail endpoint confirmed at
  `.../wday/cxs/ubc/ubcstaffjobs/job/<externalPath>`. `platform` =
  **`"Workday"`**.
- **Reddit** — real URL `https://job-boards.greenhouse.io/reddit`. Platform:
  Greenhouse (Greenhouse's own hosted board domain, unambiguous). API:
  `GET https://boards-api.greenhouse.io/v1/boards/reddit/jobs?content=true`
  (156 jobs, one call). Same as Riot: **no server-side location filter**
  (confirmed by diffing `?location=Canada` against the unfiltered response —
  identical); client-side filtering on `location.name` found **13 real
  Canada jobs** (Toronto, Remote-Ontario, Remote-BC), skewing
  Ads/Data-Science-adjacent rather than pure "Software Engineering." A
  richer endpoint, `GET https://boards-api.greenhouse.io/v1/boards/reddit/departments`,
  returns Greenhouse's actual department tree with parent/child IDs —
  top-level **`"Engineering"` department, id `16253`** (children include
  `"Ads Engineering"`, `"Machine Learning"`, `"BE Platform"`, `"Site
  Reliability"`, `"FE Platform"`) — a more precise category scope than
  string-matching, using each job's `departments[]` array (note: the
  `metadata[]` entry literally named `"Department"` was `null` on the job
  inspected — `departments[]` at the top level is the reliable field, not
  that metadata entry). `platform` = **`"Greenhouse"`**.
- **ATS Corporation** (real domain is `atsautomation.com` —
  `atscorporation.com` is an unrelated parked/for-sale domain, confirmed via
  its Akamai "forsale.godaddy.com" block page; don't confuse the two).
  Careers site `https://jobs.atsautomation.com/` redirects into
  `career5.successfactors.eu/career?...&company=atsP2` — **SAP
  SuccessFactors classic Recruiting Career Site** (RCM), a different layer
  than Scotiabank's Jobs2Web — confirmed via `/ui/rcmcareer/`,
  `/ui/rcmjobsearch/`, `/ui/ravcareer/` asset paths. **Investigation
  incomplete**: unlike Scotiabank's plain server-rendered HTML, this career
  site's search is a session/CSRF-token-driven AJAX widget (SF's internal
  "ASProxy" RPC protocol) — not callable blind with curl/httpx. The standard
  SF OData endpoint (`career5.successfactors.eu/odata/v2/JobRequisitionLocale?company=atsP2`)
  returned a bare 404, so that path is out. This needs the same treatment as
  EA's original investigation: drive the real search form once with
  Playwright, capture the exact POST it fires (URL, body shape, and
  whatever session/CSRF token it needs), then decide whether that request
  can be replayed headlessly. Not scraper-ready yet. `platform` will be
  **`"SuccessFactors"`** once confirmed.

### Intel, Oracle, Spotify, Adobe, Sony, AMD, Uber scraping approach (investigated 2026-09-19)

- **Intel** — the marketing-facing `jobs.intel.com` domain is currently dead
  (every path 301s to a broken-link redirector); the real backend is
  Workday, tenant `intel.wd1.myworkdayjobs.com/External`, CXS API confirmed
  (`total: 615` globally). Category facet `jobFamilyGroup`, "Software
  Engineering" = `ace7a3d23b7e01a0544279031a0ec85c`. **No country-level
  facet** — locations are city-granular under `locationMainGroup` →
  `locations`; Canada requires passing **both** `"Canada, Toronto"`
  (`1e4a4eb3adf1019f4237e975bf81b3ce`) and `"Virtual Canada"`
  (`3d7e019f2bb20100b6accdbea05c0000`) — confirmed Toronto-only gives 0,
  both together gives 3 (all "Virtual Canada"). Pagination: `limit`/`offset`
  body fields, standard CXS. `bulletFields` is single-element (`[reqId]`).
  `platform` = **`"Workday"`**.
- **Oracle** — its own product, **Oracle Recruiting Cloud** (Fusion Cloud
  HCM), not a third-party ATS. Public, unauthenticated REST API found via
  the CSP header on `oracle.com/careers/`:
  `GET https://eeho.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber=CX_1,facetsList=LOCATIONS;CATEGORIES,limit=20,offset=0`
  (confirmed 200, `TotalJobsCount: 2261`). Category filter:
  `selectedCategoriesFacet=<id>` from the response's own `categoriesFacet`
  array (e.g. "Product and Research" = `302958497961752`). **Canada filter
  is fuzzy, not exact** — both `location=Canada` and
  `selectedLocationsFacet=300000000106749` return the same 8-job set, but
  some have `PrimaryLocation: "United States"` (confirmed by inspection, not
  a bug on our end) — the scraper must fetch that candidate set and
  client-side-filter on `PrimaryLocation` containing `"Canada"`. Fields:
  `Id`, `Title`, `PostedDate` (already a plain ISO date — no fallback
  needed), `PrimaryLocation`, `JobFamily`/`JobFunction` (null in practice at
  this site number — don't rely on them). Pagination: standard
  `limit`/`offset`. `platform` = **`"Oracle Recruiting Cloud"`**.
- **Spotify** — `lifeatspotify.com`'s own API
  (`api.lifeatspotify.com/wp-json/animal/v1/job/search`) only does
  client-side filtering (ignores query params) and is a thin wrapper; the
  real backend ATS is **Lever**, confirmed via each job's `apply` link
  pointing at `jobs.lever.co/spotify/...`. Scrape Lever directly:
  `GET https://api.lever.co/v0/postings/spotify?mode=json` (no auth, 71
  postings in one call, `skip=N` pagination exists but isn't needed at this
  size). No server-side Canada/category filter; each posting has `country`
  (ISO-2, e.g. `"CA"`) and `categories.department` — filter client-side.
  Currently **0 Canada+Engineering** (the one Canada posting found is
  department "Data and Analytics", not Engineering — a legitimate empty
  result). Fields: `id` (UUID, stable), `text` (title), `categories.*`,
  `country`, `createdAt` (real epoch-ms, clean date), `hostedUrl`.
  `platform` = **`"Lever"`**.
- **Adobe** — Phenom People, same `phApp.ddo` blob family as RBC/BMO
  (`careers.adobe.com/us/en/search-results?category=<label>`), confirmed by
  `totalHits` changing with the category param. **Country query param does
  not work** — every variant tried (`country=Canada/CA/canada`,
  `locations=Canada`, array/bracket forms) returned identical, unfiltered
  `totalHits` still containing non-Canada jobs; there's no separate `/ca/en/`
  locale (redirects back to `/us/en`). Must fetch the category-filtered
  pages and filter **client-side** on each job's `"country"` field (full
  name, e.g. `"United States of America"`) — confirmed exactly **7 Canada
  jobs** company-wide right now. Pagination: `&from=<offset>&s=1`, 10/page,
  same not-fully-stable-sort caveat as RBC. Every job's `applyUrl` points at
  `adobe.wd5.myworkdayjobs.com` — same Phenom-front/Workday-apply
  relationship as RBC/BMO. `platform` = **`"Workday"`**.
- **Sony** — `sony.com`'s own corporate careers page is flat-403-blocked
  (Akamai, same category of block as Manulife, not investigated further).
  The real public careers site is **`sonyjobs.com`**, whose `jobs.html`
  statically embeds `<iframe src="https://sonyglobal.wd1.myworkdayjobs.com/SonyGlobalCareers">`
  — Workday, tenant `sonyglobal`, confirmed via the CXS API (`total: 111`
  globally, spans multiple Sony subsidiaries as `Company` facet values).
  Country facet `locationCountry`, Canada =
  `a30a87ed25634629aa6c3958aa2b91ea` — **the same shared cross-tenant ID**
  already seen on SOTI/CIBC/TD/Manulife. Category facet `jobFamilyGroup`,
  the Software-Engineering-equivalent value is specifically
  `"Product Development_Software"` = `bf0e94cb2dac0126e6d1bfd19e01df13`
  (distinct from a broader parent "Product Development" facet). Combined
  filter confirmed working mechanically; currently **0** jobs in that exact
  combination (Canada-only gives 1 unrelated marketing role — legitimate
  empty result for the SWE slice). Detail endpoint confirmed for real
  `startDate`. `platform` = **`"Workday"`**.
- **AMD** — **blocked, no workaround found.** `careers.amd.com` points at
  `careers-amd.icims.com` (iCIMS) as its actual system of record (no
  evidence of a secondary underlying ATS to fall back to, unlike Manulife).
  Every direct request to the iCIMS jobs-search endpoint — with or without
  browser-like headers — returns `405` with `x-amzn-waf-action: captcha`
  (an AWS WAF bot challenge; same category of problem as Manulife's Akamai
  block, different vendor/mechanism). The public careers page itself has no
  server-rendered job data to fall back to either. Not scraper-ready;
  `platform` would be **`"iCIMS"`** if a workaround is ever found. A real
  Playwright pass could confirm whether the WAF challenge is solvable
  non-interactively, but Manulife's experience suggests it may not be worth
  pursuing.
- **Uber** — **blocked, unresolved.** `careers.uber.com` → a custom in-house
  Next.js app, no third-party ATS vendor signature found anywhere in its
  rendered HTML or JS bundles. Its job-search mutation endpoint
  (`POST /api/loadSearchJobsResults`) returns `403 Missing csrf token` — an
  app-level CSRF gate, not a WAF/Cloudflare block (Cloudflare's own cookie
  was present and not the blocker). Real Canada SWE postings do exist
  (confirmed via web search of individual `.../careers/list/<id>/` pages,
  e.g. "Software Engineer II (Backend), Airports - Toronto, Canada") but
  couldn't be enumerated without a real browser session to acquire the CSRF
  token, the same technique EA's original investigation used for its opaque
  Avature facet IDs. Not scraper-ready; `platform` tentatively "Uber
  (custom)" pending that follow-up — do not record a third-party vendor name
  without further confirmation.

### Airbnb, Databricks, Stripe scraping approach (investigated 2026-09-19)

All three turned out to be **Greenhouse** under the hood despite each having
a different custom front-end. In all three cases the public,
unauthenticated Greenhouse Board API works directly and is far cleaner than
scraping the custom front-end HTML:
- `GET https://boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true`
  — tokens confirmed: `airbnb`, `databricks`, `stripe`.
- `GET https://boards-api.greenhouse.io/v1/boards/<token>/departments` — full
  department tree with per-department job counts.
- **No pagination** — each call returns the complete current job list in one
  response (confirmed: Airbnb 168 jobs matching the site's own "168 open
  positions" figure; Databricks 878; Stripe 667).
- Per-job fields: `id` (stable numeric Greenhouse job id — use as
  `external_id`), `title`, `location.name` (free text, e.g. "Toronto,
  Canada" — no separate country code field), `departments[].name`,
  `absolute_url`, `updated_at`, `first_published` (true original post date,
  confirmed distinct from `updated_at`). **`requisition_id` is unreliable**
  — Stripe always returns the literal placeholder `"See Opening ID"`,
  Airbnb returns junk (`"MULTI"`/`"ONE"`); only Databricks has a real value.
  Use Greenhouse's own `id`, never `requisition_id`, as `external_id`.
- **Airbnb**: confirmed via the job-detail "Apply Now" embed script
  (`for=airbnb`). Department for category filter: **`Software Engineering`**
  (id `77`, 38 jobs). No country facet in the API — filter client-side on
  `location.name` containing `"Canada"`. Currently **0** jobs match Canada +
  Software Engineering simultaneously (verified: Canada jobs exist, just not
  in this department right now).
- **Databricks**: confirmed via its Gatsby `page-data.json` embedding a
  `allGreenhouseJob` GraphQL type and `gh_jid=` job URLs. Two SWE-relevant
  departments: **`Engineering`** (id `4001015002`, 54 jobs) and
  **`Engineering - Pipeline`** (id `4115423002`, 140 jobs). Same
  client-side `"Canada"` substring filter on `location.name`; real matches
  found (e.g. "Senior Software Engineer - Backend", Vancouver).
- **Stripe**: confirmed via an inline JSON blob on the site with
  `"listings":[{"greenhouseId":...}]` per job. **No single "Engineering"
  department** — Stripe's tree is ~192 deeply-nested numeric-prefixed teams
  (e.g. `"8512 Terminal - Eng"`). Practical filter: department name
  containing `"Eng"` (case-insensitive) and/or title containing
  `"Engineer"` — a heuristic, not an exact facet, since no clean category
  exists here. Confirmed 29 Canada matches with this approach.
- `platform` = **`"Greenhouse"`** for all three.

### SAP scraping approach (re-investigated 2026-10-02)

The original 2026-09-19 approach (parsing the Jobs2Web `/search/` page on
jobs.sap.com) stopped working when SAP rebuilt jobs.sap.com as a Next.js
app (Vercel, behind Cloudflare). `/search/` now 301s to `/en/jobs/`, and
plain httpx gets a 403. SAP's jobs are now split across two backends with
no overlap, and `scrapers/sap.py` reads both:

- **SuccessFactors classic RCM XML feed** (SAP's main job set, 769 postings
  worldwide, 10 in Canada):
  `career5.successfactors.eu/career?company=SAP&career_ns=job_listing_summary&resultType=XML`.
  This is the same feed as Canada Life's and ATS's, but SAP's includes the
  custom fields "Work Area", "Country" and "Internal Posting Location", plus
  `ReqId` and `Posted-Date`. That's everything the scraper needs in one
  ~11 MB response, so no detail pages are fetched. These jobs aren't on the
  new jobs.sap.com, so the job link is the classic RCM page
  (`...&career_ns=job_listing&career_job_req_id=<ReqId>`), which has a
  working Apply button. **`external_id` is now the ReqId**, not the old
  Jobs2Web numeric ID.
- **SmartRecruiters**, company `SAPITBusinessSysteme`: what the new
  jobs.sap.com actually lists (51 postings, all under the "SAP IT Business
  Systeme" entity). It's scoped by the "Board Area" custom field = "Product
  & Engineering". There were 0 Canada matches on 2026-10-02, but it's
  scraped in case SAP moves more postings over.
- Scope stays Work Area = "Software-Design and Development" (2 Canada jobs
  on 2026-10-02). Other tech-ish Work Areas in the feed, if the scope ever
  widens: "Information Technology", "Software-Development Operations",
  "Software-Research", "Software-User Experience", "Software-Quality
  Assurance".

### Snowflake scraping approach (investigated 2026-09-19)

- Real URL: `https://careers.snowflake.com/us/en`. Confirmed **Phenom
  People** (same family as RBC/BMO) via the `PHPPPE_ACT` cookie and
  `phApp`/`phApp.ddo` blob — but here the job list lives at
  `phApp.ddo.eagerLoadRefineSearch.data.jobs` (a different path than RBC's).
- **Category filter confirmed working**: `?category=Engineering` drops
  `totalHits` to exactly 96, matching the facet's own aggregation count.
- **No working country filter** — `country=Canada` is silently ignored;
  `location=` only works with an exact city-level string (e.g.
  `location=Toronto, Ontario, Canada` correctly returns 6 hits) — there's no
  country-level location facet. Practical approach: filter server-side by
  `category=Engineering`, then client-side on each job's own `country`
  field (present per job) — confirmed a real match this way (`REQ18507`,
  country=Canada).
- Pagination: `from=N` in steps of 10, same convention as RBC.
- Fields: `reqId` (human-readable, stable, e.g. `"REQ20118"` — use as
  `external_id`), `title`, `country`, `city`, `category`, `department`,
  `postedDate` (real ISO date), `applyUrl`.
- **Every job's `applyUrl` points at `jobs.ashbyhq.com/snowflake/<uuid>`
  with `"externalApply": true`** — Snowflake's real underlying ATS is
  **Ashby**, not Workday; the Phenom front-end is purely a listing/branding
  layer, same relationship pattern as RBC/BMO/Manulife's Phenom-front/other-ATS-apply.
- `platform` = **`"Ashby"`**.

### Metrolinx scraping approach (investigated 2026-09-19)

- Real URL: `https://www.metrolinx.com/en/about-us/careers` links out to
  `https://ehtc.fa.ca2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1`
  — **Oracle Fusion Cloud Recruiting** (distinct from the older Oracle
  Taleo product, and a different Oracle Cloud pod than Oracle Corp's own
  careers site above).
- Public, unauthenticated REST API confirmed:
  `GET https://ehtc.fa.ca2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.secondaryLocations,flexFieldsFacet.values&finder=findReqs;siteNumber=CX_1,facetsList=LOCATIONS%3BWORK_LOCATIONS%3BTITLES%3BCATEGORIES%3BORGANIZATIONS%3BPOSTING_DATES%3BFLEX_FIELDS,limit=25,offset=0,sortBy=POSTING_DATES_DESC`.
  **The `expand=requisitionList...` param is required on every page** — omitting
  it silently returns facets with no `requisitionList` at all (looks like an
  error but isn't).
- **No country filter needed** — the `locationsFacet` shows a single
  `"Canada": 38` bucket for all 38 currently-open jobs (expected for an
  Ontario transit agency).
- **No dedicated tech/IT category currently exists** — `categoriesFacet`
  only reflects the live result set (Management, Administrative and
  Clerical, Project Management, etc.), no "Technology"/"IT" bucket right
  now. One job title (`"Manager, I&IT Project Management Office"`) hints at
  Metrolinx's internal `"I&IT"` naming convention, filed under "Project
  Management" rather than a distinct tech category. Given only 38 total
  jobs (already Canada-only), recommend pulling all of them and either
  keyword-matching titles for `I&IT`/`IT`/`Software`/`Developer`/`Systems`,
  or skipping category filtering and recording the free-text `Category`
  as-is — same "no cross-company normalization" convention as elsewhere.
- Pagination: `offset`/`limit` in the query string, page size 25, confirmed
  a real non-overlapping second page.
- Fields: `Id` (stable numeric requisition ID, use as `external_id`),
  `Title`, `PostedDate` (real absolute date), `PrimaryLocation`,
  `WorkplaceType`. `JobFamily`/`JobFunction`/`Department`/`Organization`
  are `null` on every job sampled — don't rely on them.
- `platform` = **`"Oracle Recruiting Cloud"`**.

### Eclipse Automation — investigation blocked by third-party outage (investigated 2026-09-19)

- Real URL `https://www.eclipseautomation.com/careers/` links out to
  `https://jobs.dayforcehcm.com/en-CA/eclipse/CANDIDATEPORTAL` — **Dayforce**
  (Ceridian's HCM/ATS product), company code `eclipse`.
- **Could not verify anything beyond the platform identity**: every request
  to `jobs.dayforcehcm.com` (both locale variants, with/without a browser
  UA, and even unrelated control tenant codes) redirected to
  `.../en-CA/systemUnderMaintenance`, whose body states Dayforce-powered
  career sites are undergoing scheduled maintenance platform-wide — retried
  multiple times, still down each time. This is a Dayforce-wide outage, not
  specific to Eclipse's tenant.
- **Needs a follow-up pass once Dayforce's maintenance window ends**, using
  the same method as everywhere else here (check for a JSON API vs.
  server-rendered HTML, confirm country/category filter params, confirm a
  stable job ID and posted-date field). Not scraper-ready.
- `platform` = **`"Dayforce"`** (confirmed platform identity; nothing else
  about it is confirmed).

### Meta, Amazon, Google, Apple, Microsoft, IBM, Canonical scraping approach (investigated 2026-09-19)

Investigated via real HTTP requests, plus a temporarily-installed
Playwright/Chromium session where a plain fetch didn't reveal the real API
(same pattern as EA's original investigation) — used only to observe
network calls or bypass a block, not part of the eventual scraper except
where noted for Meta.

- **Meta** — `metacareers.com` returns **HTTP 400 to every plain curl
  variant tried** (headers didn't matter) — a client-fingerprint-level
  block (TLS/HTTP2 fingerprint, not a WAF page), confirmed bypassed
  trivially by a real/headless Chromium (200 OK, real content). The real
  API is `POST https://www.metacareers.com/graphql`, but **the request body
  carries ~10 Meta-internal anti-automation tokens minted by the page's own
  JS on load** (`lsd`, `jazoest`, `__hs`, `__dyn`, `__csr`, etc.) — these
  are session-bound, not hardcodable secrets. **This means Meta cannot be
  scraped with lightweight periodic HTTP calls at all** — unlike every
  other company in this project, it would need a full Playwright browser
  session on every scrape run. Category facet: `team_display_name`,
  "Software Engineering" is one of ~25 values. Location facet is per-city,
  not per-country (`montreal`, `toronto`, `vancouver`, `ottawa`,
  `canada-remote`, `sturgeon-county-dc`, each carrying `"country":"Canada"`)
  — would need to pass all of these IDs together. Fields: `id` (stable
  numeric string, use as external_id), `title`, `locations[]` (display
  strings, not IDs), `teams`. **No posted-date field at all** — falls back
  to `first_seen_at`. Pagination not fully determined (unfiltered query
  returned all 989 jobs in one response). `platform` =
  **`"Meta Careers (custom, in-house)"`**.
- **Amazon** — `https://www.amazon.jobs/en/search.json`, a fully open JSON
  API, no bot-blocking at all, no auth needed. Confirmed working combined
  filter: `?category[]=software-development&country=CAN&result_limit=20&offset=0`
  → 179 hits. Note the asymmetric quirk: `category[]=` (array form) and
  `country=` (singular form) are the only forms that actually filter —
  `category=` singular and `country[]=` array are silently ignored, confirmed
  by testing all four combinations. Pagination: `offset`/`result_limit` in
  the query string. Fields: `id_icims` (legacy field name, but Amazon's
  system is not actually iCIMS — still the stable ID, use as external_id),
  `title`, `job_category` (exact match), `city`, `state`, `country_code`,
  `posted_date` (real parseable date), `job_path` (prefix with
  `https://www.amazon.jobs`). `platform` = **`"Amazon Jobs (custom,
  in-house)"`**.
- **Google** — `https://www.google.com/about/careers/applications/jobs/results`,
  fully open, no blocking, and **fully server-rendered in plain HTML** (an
  initial test query looked like a JS-only SPA with 0 results, but that was
  a bad query — confirmed real server-rendered data with a working query).
  Confirmed working request: `?location=Canada&q=%22Software%20Engineer%22`
  → real matches directly in the curl'd HTML. **No true category/team
  facet** — confirmed via Playwright that the UI's own "What do you want to
  do?" field just resolves to the same free-text `q=` quoted-phrase search,
  not a separate facet param, so category filtering has the same
  recall/precision caveat as EA's free-text approach. `location=Canada` IS
  a real facet (confirmed via the results-page location chip).
  Pagination: `page=N` (1-indexed), page size 20. Fields: stable numeric
  job ID from the `ssk` HTML attribute (also in the detail URL), title,
  location string(s), experience-level tag. **No posted date anywhere** —
  falls back to `first_seen_at`. `platform` = **`"Google Careers (custom,
  in-house)"`**.
- **Apple** — `https://jobs.apple.com/en-us/search?location=canada-CANC`
  (`canada-CANC` confirmed as Canada's location facet ID), fully open, no
  blocking, server-rendered via an embedded
  `window.__staticRouterHydrationData` JSON blob (same "parse one big
  embedded blob" pattern as RBC's `phApp`, React-Router-flavored instead of
  Phenom). **No working URL-level category facet** — `team=`/`teams=`/
  `role=` params tried, none changed the result count; the only filtering
  param that works is free-text `search=`, with the same off-target-hit
  caveat as Google. **Recommended approach**: fetch `location=canada-CANC`
  unfiltered (34 jobs, `page=1,2`, page size 20), then filter **client-side**
  on the embedded JSON's `team.teamName == "Software and Services"` (present
  on every job object even though not exposed as a URL filter) — exact
  precision without the free-text noise. Fields (from
  `loaderData.search.searchResults[]`): `id` (stable, use as external_id),
  `postingTitle`, `postDateInGMT` (real ISO datetime — use as posted_date),
  `team.teamName`/`teamCode`, `locations[].name`/`countryName`, `reqId`.
  Apply happens directly on `jobs.apple.com`, no external ATS. `platform` =
  **`"Apple Jobs (custom, in-house)"`**.
- **Microsoft** — real URL resolves to
  `https://apply.careers.microsoft.com/careers`. **Platform: Eightfold**,
  confirmed unambiguously via response headers (`x-ef-ns: smartapply`,
  `x-ef-req-endpoint`, `x-ef-trace-id`) and CSP referencing
  `docs.eightfold.ai`. The page is a client-rendered SPA; the real search
  API (`GET https://apply.careers.microsoft.com/api/pcsx/search?domain=microsoft.com&query=<text>&location=<text>&start=<offset>`)
  was found via Playwright network capture. Both `query` and `location` are
  plain free-text params, no opaque facet IDs — confirmed `location=Canada`
  alone returns 63 real Canadian jobs. **No working `department=` facet
  param** (silently ignored) — recommended approach is to fetch
  `location=Canada` unfiltered, then filter client-side on each job's own
  `department == "Software Engineering"` field. Pagination: `start=` offset,
  page size 10. Fields: `id`, `displayJobId`/`atsJobId` (human req number,
  recommend as external_id), `name` (title), `department`, `locations`,
  `postedTs` (real Unix timestamp), `positionUrl` (prefix with
  `https://apply.careers.microsoft.com`). `platform` = **`"Eightfold"`**.
- **IBM** — two distinct layers. **Search/discovery**:
  `https://www.ibm.com/careers/search`, backed by IBM's own custom
  Elasticsearch-backed index, not a third-party ATS — found via Playwright
  network capture: `POST https://www-api.ibm.com/search/api/v2` with raw
  Elasticsearch query DSL exposed directly to the client, **no bot-blocking
  at all**, works with plain curl. Confirmed combined filter:
  `post_filter.bool.must = [{"term":{"field_keyword_08":"Software Engineering"}},{"term":{"field_keyword_05":"Canada"}}]`
  → 32 real Canadian software-engineering hits (of 379 global Software
  Engineering jobs, of 1884 total). Pagination: standard ES `size`/`from`
  in the POST body. Fields: `title`, `url` (→
  `https://careers.ibm.com/careers/JobDetail?jobId=<ID>`, numeric jobId is
  the external_id), `description`. **No posted-date field available at
  all** — falls back to `first_seen_at`. **Application/detail layer**:
  `careers.ibm.com/careers/JobDetail?jobId=<ID>` confirmed running on
  **Avature** (`<meta name="avature.portal.id">` etc., same ATS as EA) and
  protected by an **AWS WAF JS challenge** (curl gets `202 Accepted`,
  `Content-Length: 0`, `x-amzn-waf-action: challenge` — never returns
  content; a real/headless Chromium passes through automatically by
  executing the challenge). This layer is unnecessary to touch since the
  search-index layer already provides everything needed (and has no posted
  date to offer anyway). `platform` = **`"Avature"`** (the actual
  application system of record), noting job discovery goes through IBM's
  own Elasticsearch API instead of Avature's own search — analogous in
  spirit to Manulife's two-tier finding, though here both tiers are IBM's
  own domains.
- **Canonical** — `https://canonical.com/careers` embeds
  `job-boards.greenhouse.io/canonical/jobs/<id>` links — **Greenhouse**,
  confirmed directly. API: `GET https://boards-api.greenhouse.io/v1/boards/canonical/jobs?content=true`
  → 304 jobs, no bot-blocking, no auth, no pagination needed. **No clean
  Canada facet** — Canonical is remote-first; `offices[].name` values are
  broad regional buckets (`"Home Based - Americas"`, etc.) plus one literal
  `"Office Based - Toronto, Canada"`. Most Canada-based remote engineers
  would actually be filed under the country-agnostic `"Home Based -
  Americas"` bucket (which also includes the US and Latin America), so a
  strict Canada filter using only the office field would under-count — a
  real, confirmed data-shape limitation to document as a caveat, not a bug.
  **No single "Software Engineering" department either** — confirmed
  separate sub-departments (`"Charm Engineering"`, `"Cloud Engineering"`,
  `"Devices Engineering"`, `"SRE"`, `"SaaS Engineering"`, `"Web
  Engineering"`, etc.) — a scraper would need to match against this whole
  set rather than a single exact string. Fields: `id` (numeric, stable,
  use as external_id), `title`, `absolute_url`, `location.name`,
  `departments[].name`, `offices[].name`, `first_published` (true original
  posting date, better than `updated_at`). `platform` = **`"Greenhouse"`**.

### Shopify, Thomson Reuters, Salesforce, Autodesk, Sun Life scraping approach (investigated 2026-09-25)

- **Shopify** — real ATS is **Ashby** (jobs link as
  `shopify.com/careers?ashby_jid=<uuid>`), but there's no public Ashby board
  (posting API 404s for every plausible slug; Greenhouse/Lever 404 too).
  The careers page is a React Router app, and its loader data is available
  on its own at `GET https://www.shopify.com/careers.data`. It's in React
  Router's "turbo-stream" encoding (a flat, index-referenced JSON array),
  which `scrapers/shopify.py` decodes. Jobs are at
  `["($locale)/careers"].data.jobPostingsWithJobs[].jobPosting` (`id`
  UUID = external_id, `title`, `teamName`, `publishedDate` real ISO date,
  `locationIds`), with location UUIDs resolved through the sibling
  `atsLocations` list. **Canada caveat**: all 44 Engineering postings are
  listed only under the remote region "Americas", with no Canadian city, so
  the scraper matches "Americas" as well as any Canadian location. This is
  the same limitation as Canonical. `platform` = **`"Ashby"`**.
- **Thomson Reuters** — Workday, `thomsonreuters.wd5.myworkdayjobs.com/External_Career_Site`.
  Category facet is a custom field
  `CF_Job_Posting_Anchor_Job_Category_EEB_Extended`, "Technology Careers" =
  `9276a62d4e68100204e60c54e1cc0001`; `Location_Country` Canada = shared
  `a30a87ed…` ID → 53 jobs. **`bulletFields` is `[cities, provinces, reqId]`**:
  the req ID is the *last* element here, not the first, and
  `locationsText` is null, so location comes from the detail endpoint.
- **Salesforce** — Workday, `salesforce.wd12.myworkdayjobs.com/External_Career_Site`.
  `jobFamilyGroup` "Software Engineering" = `14fa3452ec7c1011f90d0002a2100000`;
  country facet has a long custom-field name
  (`CF_-_REC_-_LRV_-_Job_Posting_Anchor_-_Country_from_Job_Posting_Location_Extended`)
  but uses the shared Canada ID. Currently only 1 match. I cross-checked that
  against passing every "Canada - <city>" `locations` value and got the same
  result, so it's genuinely 1.
- **Autodesk** — Workday tenant `autodesk.wd1.myworkdayjobs.com`, site `Ext`
  (confirmed by current public Toronto job links). During investigation the
  CXS API returned `404 not found: Job_Posting_Site_ID=Ext` and the web page
  302'd to `myworkday.com/wday/drs/outage?t=autodesk&s=ext`, which is a
  Workday outage/maintenance redirect for this tenant. `autodesk.com/careers`
  itself is Akamai-403'd. **Retry the CXS facet discovery once the outage
  clears.** (Its separate `uni` site does respond: 27 student jobs.)
- **Sun Life** — Workday, `sunlife.wd3.myworkdayjobs.com/Experienced-Jobs`.
  No `jobFamilyGroup`; `jobFamily` values "IT - Application Development"
  (`b18e449d87914e8db756066e35d5f247`), "IT - Technology Services"
  (`fc46f3fb6ab24457be62e0b15c2c0101`), "IT - Digital Development"
  (`9d42de6b15aa0173c155daaa6201da7f`) + `Location_Country` Canada → 17
  jobs. Location from the detail endpoint (multi-location "3 Locations"
  placeholder in the list, same as Manulife).

### Shared ATS helpers (added 2026-09-25)

Per-platform helpers live in `scraper/scrapers/`, and every company on a
shared ATS uses one, so its module is just config + its investigation
notes (docstring). **A new company on one of these platforms should be a
small config module calling the helper**, not a copy of another company's
scraper. Each helper's docstring explains the API and the per-tenant hooks
(`job_filter`, `category_fn`, etc.):

- `workday_cxs.py` — Workday CXS (list + per-job detail). Takes `jobReqId`
  from the detail endpoint as `external_id` (the req ID's position in
  `bulletFields` varies by tenant). Shows Canadian locations first when a
  posting also has `additionalLocations`, because a country facet matches
  a posting if *any* of its locations is in that country. `job_filter` can
  filter on the detail's `country.descriptor` for tenants that have no
  country facet.
- `greenhouse.py`: department matching walks the `/departments` tree (a
  parent name matches all sub-teams), with an optional exclude set. Canada
  is matched on `location.name` + `offices[]` by default, with a per-company
  override where offices are misleading (Dropbox, Geotab).
- `ashby.py` — `api.ashbyhq.com/posting-api/job-board/<org>`.
- `jobs2web.py` — SuccessFactors Jobs2Web (Scotiabank's layer): `/go/<cat>/<id>/`
  landing pages, or `/search/` + `startrow` when there are none.
- `phenom.py` — `phApp.ddo` blob, `?category=` per request.
- `dayforce.py` — Dayforce candidate portal JSON API (see Questrade below).
- `eightfold.py` — Eightfold `/api/pcsx/search` (Microsoft, Autodesk).
  Liberty Mutual's older `/api/apply/v2/jobs` API is not covered.
- `oracle_recruiting.py` — Oracle Recruiting Cloud REST `findReqs` finder
  (Oracle, Metrolinx).
- `lever.py` — Lever postings API (Spotify).
- `smartrecruiters.py` — SmartRecruiters posting API (Ubisoft, Arista),
  scoped by a custom field.
- `talentbrew.py` — Radancy TalentBrew career sites (Intuit, Synopsys).
- Still bespoke: the custom in-house sites (Amazon, Google, Apple, IBM,
  Meta, Shopify), SAP (SuccessFactors feed plus the SmartRecruiters
  helper), EA and National Bank (Avature, but different page templates and
  date sources), Liberty Mutual, Kinaxis, Xanadu (HiBob),
  Vidyard (Kula) and FreshBooks (Gem).
- `base.CANADA_PATTERN` is the shared free-text Canada matcher. It covers
  every province and territory (names, main cities, and whole-word codes),
  so "San Francisco, CA" doesn't match. SK/NL/PE aren't matched as bare
  codes because they collide with ISO country codes (Slovakia, Netherlands,
  Peru).
- Scope is all of Canada, never a single province. Workday tenants without
  a country facet pass every Canadian `locations` ID (re-checked
  2026-10-02: SOTI, Ontario Teachers', PayPal and Intel each have only
  Ontario locations, so their lists are complete).

### Fourth wave, batches 2–6 scraping approach (investigated 2026-09-25)

Company-specific findings. Each module's docstring has the full detail.

- **Ashby** (`cohere`, `wealthsimple`, `1password` orgs): no server-side
  filtering. Canada = address country or any secondary location. Cohere
  departments: "Engineering & Infra", "Modeling", "Inference" (excluding
  contract "Data Quality" annotation roles). Wealthsimple: "Data &
  Engineering". 1Password: "Technology" (mostly "Remote (United States |
  Canada)").
- **Greenhouse** (`faire`, `cloudflare`, `dropbox`, `pinterest`,
  `instacart`, `coinbase`, `geotab`, `d2l`):
  - Cloudflare's `location.name` is only "Hybrid"/"Distributed", so the
    city comes from `offices`.
  - Cloudflare's "Solution Engineering" is pre-sales, so it's excluded.
  - Dropbox's engineering sits under the top-level "EPD" org; "Product
    Team" is excluded.
  - Pinterest: the "Engineering, Product and Design (L2)" org minus Design
    and Core Product.
  - Instacart: everything under "Engineering" except Professional Services.
  - D2L's Lever board is stale (2019); Greenhouse is the live one.
- **National Bank** (`emplois.bnc.ca`, Avature like EA):
  - The area-of-interest field (`6472`) has AJAX-only option IDs, found
    with Playwright: 25044 IT, 25045 AI, 25047 Web & digital, 25059 BI &
    data.
  - The listing is a plain GET (`SearchJobs/?6472[]=…&listFilterMode=1`,
    `jobOffset` in steps of 20).
  - The RSS feed caps at 20 items (same as EA), so the posted date and
    category come from each detail page.
- **Intact / Clio / Arctic Wolf** (Workday): none of these tenants has a
  country facet, so Canada is filtered on the detail's `country`.
  - Intact's front-end `careers.intactfc.com` has its `/api/jobs`
    Akamai-403'd. Its apply links reveal the tenant
    `intactfc.wd3…/intactfc`.
  - Clio: clio.com is Cloudflare-403'd. The tenant is
    `clio.wd3…/ClioCareerSite`.
  - Arctic Wolf's tenant is `arcticwolf.wd1…/External`.
- **Interac** (`interac.wd3…/Interac`) and **Workday**
  (`workday.wd5…/Workday`) are plain Workday; Workday uses the shared
  Canada ID.
- **Canada Life**: the SuccessFactors classic RCM XML feed works
  (`career5.successfactors.eu/career?company=thegreatweP2&career_ns=job_listing_summary&resultType=XML`),
  but it has only title, req ID and date, and it isn't well-formed XML.
  The Jobs2Web site `jobs.canadalife.com/go/All-Jobs/9170201/` has a
  Department column, so the scraper filters on "Digital Technology".
  The same XML feed led to ATS Corporation's Jobs2Web site (see below).
- **Rogers**: Jobs2Web `/go/Digital-&-Technology/9547900/` (a second,
  stale ID 8824700 errors).
- **TELUS**: Jobs2Web `/search/` only.
  - **Zero tech postings as of 2026-09-25**: everything is retail, sales
    or health. Departments are matched by tech keyword so new tech roles
    get picked up.
  - `jobs.telusdigital.com` is TELUS Digital, a separate subsidiary.
- **Bell / OpenText**: Phenom front-ends with no `applyUrl` in the blob;
  the job pages reference SuccessFactors.
  - OpenText's `country` is ISO-3 ("CAN") and must be filtered
    client-side, since `country=` is ignored.
- **Questrade**: Dayforce, namespace `qfg`.
  - The search API 403s without a NextAuth CSRF token. Get it from
    `GET /api/auth/csrf` and send it back as `x-csrf-token`; that works
    from plain httpx.
  - The department filter `departmentId` takes a *single* int; it was
    found in the JS bundle.
  - Tech = departments prefixed "Technology :" / "TSS :".
  - Postings in Argentina and Israel are filtered out by
    `isoCountryCode`.
  - Dayforce was back up on 2026-09-25, which also unblocked Eclipse
    Automation (see below).
- **Ubisoft**: SmartRecruiters company `Ubisoft2`. `country=ca` filters
  server-side, and scope is the "Job Family" custom field (Software
  Development, Information & Systems, Data). English and French duplicate
  postings are both kept.
- **Kinaxis**: iCIMS behind a Jibe front-end, with open JSON at
  `join.kinaxis.com/api/jobs?page=N`. Filtered client-side on
  `country_code == "CA"` and category Engineering / Information Technology.

### ATS Corporation and Eclipse Automation, unblocked (2026-09-25)

- **ATS Corporation** (`scrapers/atscorp.py`):
  - The SuccessFactors classic RCM XML feed
    (`career5.successfactors.eu/career?company=atsP2&career_ns=job_listing_summary&resultType=XML`)
    has only titles and req IDs. But opening a job from it redirects to a
    **Jobs2Web** site, `jobs.atsautomation.com`. The earlier investigation
    only ever saw its root redirect into the classic RCM.
  - Category page: `/go/Engineering%2C-Design%2C-&-Technical-Services/4455701/`,
    86 jobs worldwide, 22 in Canada (Cambridge ON, Woodbridge ON, Montréal).
  - It uses the newer **tile** template (`li.job-tile`) rather than the
    table template, and its count marker reads "Showing X to Y of N".
    `scrapers/jobs2web.py` handles both.
  - Past the last page it keeps re-serving the final page, so a naive count
    inflates totals. The helper dedupes and stops when a page adds no new
    IDs.
  - A separate `/PA/` site is ATS's German brand.
- **Eclipse Automation** (`scrapers/eclipse.py`): Dayforce namespace
  `eclipse`, via `scrapers/dayforce.py`.
  - 48 postings, all Cambridge ON.
  - Only 3 departments are defined, and most postings (including "AI
    Software Engineer") have none. So jobs are filtered by title keyword
    (software/developer/engineer/IT/AI/data/SCADA/controls) instead of
    department.
- **Autodesk** (`scrapers/autodesk.py`): moved to **Eightfold** at
  `jobs.autodesk.com/careers` (the URL came from the user). The old
  Workday site `autodesk.wd1.myworkdayjobs.com/Ext` now 302s to Workday's
  outage page and its CXS API says the site ID doesn't exist, so don't go
  back to it. `autodesk.com/careers` is Akamai-blocked even to headless
  Chromium.
  - Same `pcsx` search API as Microsoft:
    `/api/pcsx/search?domain=autodesk.com&location=Canada&start=N`.
  - `department` holds payroll values here ("Non-Commission"), so scope
    comes from the repeatable `filter_job_category` param instead:
    development engineering, artificial intelligence, cybersecurity,
    technology. That was 7 of 16 Canadian jobs (62 worldwide) on
    2026-09-25.
  - `postedTs` is 0, so the date comes from `creationTs`.

### Fifth wave scraping approach (investigated 2026-09-25)

Each module's docstring has the details (board tokens, facet IDs, counts).
Things worth knowing across the batch:

- **Board names aren't always the company name**: Ada is `ada18`, League
  is `leagueinc`, Neo is `neofinancial`, Arista is `AristaNetworks`.
  DoorDash has per-region Greenhouse boards, and `doordashcanada` is the
  Canadian one (the US board's only "Canada" hits are Vancouver, WA).
- **Ashby `department` isn't always the discipline**: Hopper and Loopio
  put it in `team`, so `ashby.py` now takes `departments=None` plus a
  `job_filter`.
- **Workday tenants without a country facet** (Cisco, Mastercard, PayPal,
  Ontario Teachers') are filtered by passing every Canadian `locations`
  ID. That avoids fetching hundreds of detail pages (Cisco has ~670
  matching jobs worldwide). A new Canadian city on those tenants won't be
  picked up until its ID is added.
- **Tenants with no category facet** (ApplyBoard, Hydro One, Bank of
  Canada) filter by title keyword. Cadence keeps every Canadian posting.
- **Oracle Recruiting multi-category**: `selectedCategoriesFacet` takes
  semicolon-joined IDs (Nokia, Definity, Fortinet). Nokia's API lives on
  the pod host `fa-evmr-saasfaprod1.fa.ocs.oraclecloud.com`, not on
  jobs.nokia.com.
- **Currently empty, but working**: Datadog (no Canadian office), PayPal,
  ApplyBoard, Loblaw Digital (its Workday sites return 0 postings), Vidyard
  and FreshBooks (no tech postings).
- **Figma caveat**: its postings' location says SF/NY, but 53 are tagged
  with a "Canada" office, and those are counted as Canada.
- **Newly seen platforms**:
  - HiBob (Xanadu): `GET /api/job-ad` with a `companyidentifier` header.
  - Kula (Vidyard): jobs embedded in the Next.js RSC payload.
  - Gem (FreshBooks): `api.gem.com/job_board/v0/<org>/job_posts/`, shaped
    like Greenhouse.
  - TalentBrew (Intuit, Synopsys): `/search-jobs/results` XHR, with the
    Canada GeoNames ID 6251999 as the country facet.
- **Not scraper-ready** (don't retry without new information):
  - **CGI** (`cgi.njoyn.com`) and **Ontario Public Service**
    (`gojobs.gov.on.ca`): both redirect every plain HTTP request to a
    Radware bot-manager challenge (`validate.perfdrive.com`).
  - **Tesla**: `tesla.com/cua-api/...` is Akamai "Access Denied".
  - **CN**: Cornerstone (`cn360.csod.com`). The page's anonymous token
    works against `us.api.csod.com/rec-job-search/external/jobs`, but every
    payload tried returned `totalCount: 0`. It needs a Playwright capture
    of the real search request, and Playwright couldn't launch in the
    sandbox this was investigated from.
  - **Siemens**: Avature (`jobs.siemens.com`). Like EA, its country and
    category facet IDs are AJAX-only and need a Playwright pass. The
    free-text `SearchJobs/Canada` keyword search paginates in steps of 6,
    and `jobOffset` repeats pages.

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
