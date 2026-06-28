"""
Standalone sync script: extract criteria for all pending jobs.
Run after scraping: python scripts/extract_pending.py
Uses psycopg2 (sync) so long Gemini calls never block or timeout the DB connection.
"""
import json
import os
import sys
import time

import psycopg2

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "apps", "api"))

from extractor import extract_criteria

DB_URL = os.environ["DATABASE_URL_SYNC"]


def get_pending(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, raw_text FROM jobs WHERE status = %s LIMIT 50",
            ("pending_extraction",),
        )
        return [{"id": str(r[0]), "title": r[1], "raw_text": r[2]} for r in cur.fetchall()]


def mark_job(conn, job_id: str, status: str, criteria: dict | None):
    with conn.cursor() as cur:
        if criteria:
            cur.execute(
                "UPDATE jobs SET status=%s, criteria=%s, updated_at=NOW() WHERE id=%s",
                (status, json.dumps(criteria), job_id),
            )
        else:
            cur.execute(
                "UPDATE jobs SET status=%s, updated_at=NOW() WHERE id=%s",
                (status, job_id),
            )
    conn.commit()


def main():
    conn = psycopg2.connect(DB_URL)
    jobs = get_pending(conn)
    print(f"[Extract] {len(jobs)} jobs pending extraction")

    if not jobs:
        print("[Extract] Nothing to do.")
        conn.close()
        return

    ok = fail = 0
    for i, job in enumerate(jobs, 1):
        title = job["title"][:60].encode("ascii", errors="replace").decode()
        print(f"[{i}/{len(jobs)}] {title} ...", end=" ", flush=True)

        criteria = extract_criteria(job["raw_text"] or job["title"])
        if criteria:
            mark_job(conn, job["id"], "active", criteria.model_dump())
            print("active")
            ok += 1
        else:
            mark_job(conn, job["id"], "extraction_failed", None)
            print("FAILED")
            fail += 1

    conn.close()
    print(f"\n[Extract] Done: {ok} active, {fail} failed")


if __name__ == "__main__":
    main()
