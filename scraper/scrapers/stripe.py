"""Stripe careers scraper, scoped to Canada + Engineering (heuristic match).

Stripe's public-facing careers site is custom-built, but embeds an inline
JSON blob with `"listings":[{"greenhouseId":...}]` per job — the real ATS is
Greenhouse. See CLAUDE.md's "Airbnb, Databricks, Stripe scraping approach"
section for how this was found.

- `GET /v1/boards/stripe/jobs?content=true` returns the entire current job
  list in one response — no pagination needed.
- Greenhouse's public API has no server-side location filter, so Canada is
  matched client-side on each job's `location.name` containing "Canada".
- Unlike Databricks/Riot/Reddit, Stripe has no single "Engineering"
  department to match by id — its department tree is ~192 deeply nested,
  numeric-prefixed teams (e.g. "8512 Terminal - Eng"). Per CLAUDE.md's
  recommended heuristic, a job counts as Engineering-scoped if any of its
  departments' names contain "eng" (case-insensitive, catches "- Eng" /
  "Engineering" suffixes) or its title contains "engineer". This is a
  heuristic, not an exact facet — confirmed by CLAUDE.md to land ~29 Canada
  matches when investigated; the live count may drift.
- `requisition_id` is an unreliable placeholder for Stripe (always literal
  "See Opening ID", confirmed in CLAUDE.md) — Greenhouse's own `id` is used
  as `external_id` instead.
"""

from .base import NormalizedJob
from .greenhouse import location_name_is_canada, scrape_greenhouse


def scrape() -> list[NormalizedJob]:
    return scrape_greenhouse(
        name="Stripe",
        board_token="stripe",
        departments=None,
        job_filter=_is_engineering,
        is_canada=location_name_is_canada,
    )


def _is_engineering(raw: dict) -> bool:
    if "engineer" in raw["title"].lower():
        return True
    return any("eng" in dept["name"].lower() for dept in raw.get("departments") or [])
