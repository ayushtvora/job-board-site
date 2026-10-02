"""OpenAI careers scraper (Canada / engineering, research and technical roles).

Also covers "ChatGPT", which is OpenAI's product rather than a separate
employer. Ashby org `openai` (openai.com/careers links to
jobs.ashbyhq.com/openai), via scrapers/ashby.py.

- 828 postings worldwide, 7 in Canada (2026-10-02), all "Ontario - Remote"
  in the "User Operations" department (support engineers and trust & safety).
- Departments are disciplines here. Scope is the technical ones, plus any
  title containing "Engineer" in other departments, which picks up
  Toronto's support-engineer roles without the rest of User Operations.
"""

from .ashby import scrape_ashby
from .base import NormalizedJob

TECH_DEPARTMENTS = {
    "Applied AI",
    "Research",
    "Scaling",
    "Security",
    "Consumer Devices",
    "Forward Deployed Engineering",
    "Data Science",
    "Safety Systems",
    "Core Product & Platform",
    "IT",
    "Corporate Security",
}


def _matches(raw: dict) -> bool:
    return (raw.get("department") or "").strip() in TECH_DEPARTMENTS or "engineer" in raw["title"].lower()


def scrape() -> list[NormalizedJob]:
    return scrape_ashby(name="OpenAI", org="openai", departments=None, job_filter=_matches)
