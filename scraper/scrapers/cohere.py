"""Cohere careers scraper, scoped to Canada + engineering/research departments.

Ashby public job-board API (org `cohere`), via the shared helper in
scrapers/ashby.py. Investigated 2026-09-25: 147 jobs total, 92 with a
Canadian primary or secondary location (Toronto is Cohere's HQ).

Department scope — Cohere's Ashby `department` values that are engineering
work: "Engineering & Infra" (product/platform/infra/security SWE teams),
"Modeling" (research + training infrastructure), and "Inference" (model
serving). Excluded: "Data Quality (Contract)" — contract annotation roles,
not engineering jobs, despite team names like "Code Annotation".
"""

from .ashby import scrape_ashby
from .base import NormalizedJob

DEPARTMENTS = {"Engineering & Infra", "Modeling", "Inference"}


def scrape() -> list[NormalizedJob]:
    return scrape_ashby(name="Cohere", org="cohere", departments=DEPARTMENTS)
