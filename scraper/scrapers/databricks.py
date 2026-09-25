"""Databricks careers scraper, scoped to Canada + Engineering (incl. Engineering - Pipeline).

Databricks' public-facing careers site is a Gatsby front-end, but every job
is really served by Greenhouse's public Board API — confirmed via the site's
`page-data.json` embedding a `allGreenhouseJob` GraphQL type and `gh_jid=`
job URLs. See CLAUDE.md's "Airbnb, Databricks, Stripe scraping approach"
section for how this was found.

- `GET /v1/boards/databricks/jobs?content=true` returns the entire current
  job list in one response — no pagination needed.
- Greenhouse's public API has no server-side location filter, so Canada is
  matched client-side on each job's `location.name` containing "Canada".
- Two departments are the SWE-relevant scope here, matched by id (names are
  stable but ids are the confirmed-durable identifier): "Engineering"
  (4001015002) and "Engineering - Pipeline" (4115423002).
- `requisition_id` is a real, reliable value for Databricks (unlike
  Stripe/Airbnb, where CLAUDE.md notes it's a placeholder) but Greenhouse's
  own `id` is used as `external_id` anyway, for consistency with the other
  Greenhouse scrapers in this codebase.
- `first_published` is the true original posting date (confirmed distinct
  from `updated_at`, which changes on any edit).
"""

from .base import NormalizedJob
from .greenhouse import location_name_is_canada, scrape_greenhouse

# Department ids 4001015002 and 4115423002 (see module docstring).
DEPARTMENTS = {"Engineering", "Engineering - Pipeline"}


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(
        name="Databricks",
        board_token="databricks",
        departments=DEPARTMENTS,
        is_canada=location_name_is_canada,
    )
