"""Microsoft careers scraper, scoped to Canada + Software Engineering.

Real careers URL resolves to `https://apply.careers.microsoft.com/careers`,
a client-rendered SPA. Platform: Eightfold, confirmed via response headers
(`x-ef-ns: smartapply`, `x-ef-req-endpoint`, `x-ef-trace-id`) and a CSP
referencing `docs.eightfold.ai`. See CLAUDE.md's "Meta, Amazon, Google,
Apple, Microsoft, IBM, Canonical scraping approach" section (Microsoft
bullet) for how this was found.

- Real search API: `GET .../api/pcsx/search?domain=microsoft.com&query=<text>&location=<text>&start=<offset>`.
  `query` and `location` are plain free-text params, no opaque facet IDs.
  `location=Canada` alone is confirmed to return real Canadian jobs (~63 at
  investigation time).
- **No working `department=` facet param** (silently ignored) — this
  scraper fetches `location=Canada` unfiltered and filters client-side on
  each job's own `department == "Software Engineering"` field.
- Pagination: `start=` offset, page size 10 — loop until an empty page.
"""

from .base import NormalizedJob
from .eightfold import scrape_eightfold


def scrape() -> list[NormalizedJob]:
    return scrape_eightfold(
        name="Microsoft",
        base_url="https://apply.careers.microsoft.com",
        domain="microsoft.com",
        job_filter=lambda raw: raw.get("department") == "Software Engineering",
    )
