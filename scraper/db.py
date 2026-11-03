import os
from datetime import datetime

import psycopg

from scrapers.base import NormalizedJob, job_cities, job_field


def get_connection() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


def record_scrape_run(
    conn: psycopg.Connection,
    company_slug: str,
    started_at: datetime,
    finished_at: datetime,
    status: str,
    error_message: str | None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO scrape_runs (company_id, started_at, finished_at, status, error_message)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (company_slug, started_at, finished_at, status, error_message),
        )
    conn.commit()


def upsert_jobs_and_cleanup(conn: psycopg.Connection, company_slug: str, jobs: list[NormalizedJob]) -> None:
    """Upsert every job seen this run, then reconcile rows that weren't seen:
    keep-but-deactivate if applied, delete otherwise. Never touches applied,
    applied_at, or will_apply — those are only ever changed by the web app.
    """
    seen_ids = [job["external_id"] for job in jobs]

    with conn.cursor() as cur:
        for job in jobs:
            cur.execute(
                """
                INSERT INTO jobs (
                    company_id, external_id, title, url, location, category,
                    posted_date, platform, field, cities, first_seen_at, last_seen_at, is_active
                )
                VALUES (%(company_id)s, %(external_id)s, %(title)s, %(url)s, %(location)s,
                        %(category)s, %(posted_date)s, %(platform)s, %(field)s, %(cities)s, now(), now(), true)
                ON CONFLICT (company_id, external_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    url = EXCLUDED.url,
                    location = EXCLUDED.location,
                    category = EXCLUDED.category,
                    posted_date = EXCLUDED.posted_date,
                    platform = EXCLUDED.platform,
                    field = EXCLUDED.field,
                    cities = EXCLUDED.cities,
                    last_seen_at = now(),
                    is_active = true
                """,
                {
                    "company_id": company_slug,
                    **job,
                    "field": job_field(job["title"]),
                    "cities": job_cities(job["location"]),
                },
            )

        cur.execute(
            """
            UPDATE jobs SET is_active = false
            WHERE company_id = %(company_id)s AND is_active = true AND applied = true
              AND NOT (external_id = ANY(%(seen_ids)s))
            """,
            {"company_id": company_slug, "seen_ids": seen_ids},
        )
        cur.execute(
            """
            DELETE FROM jobs
            WHERE company_id = %(company_id)s AND applied = false
              AND NOT (external_id = ANY(%(seen_ids)s))
            """,
            {"company_id": company_slug, "seen_ids": seen_ids},
        )


def claim_pending_scrape_request(conn: psycopg.Connection) -> int | None:
    """Atomically claim the oldest pending on-demand scan request, if any.

    FOR UPDATE SKIP LOCKED means a request already claimed by an overlapping
    poll can't be claimed twice.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE scrape_requests
            SET status = 'running', started_at = now()
            WHERE id = (
                SELECT id FROM scrape_requests
                WHERE status = 'pending'
                ORDER BY requested_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id
            """
        )
        row = cur.fetchone()
    conn.commit()
    return row[0] if row else None


def finish_scrape_request(
    conn: psycopg.Connection, request_id: int, status: str, error_message: str | None
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE scrape_requests
            SET status = %s, error_message = %s, finished_at = now()
            WHERE id = %s
            """,
            (status, error_message, request_id),
        )
    conn.commit()
