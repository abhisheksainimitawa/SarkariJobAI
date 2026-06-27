"""
Entry point for GitHub Actions cron: scrape → extract → save to DB.
Run manually: python scripts/run_pipeline.py [--source ssc] [--dry-run]
"""
import argparse
import asyncio
import hashlib
import os
import sys

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.scrapers import ALL_SCRAPERS
from scripts.extractor import extract_criteria

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_async_engine(DATABASE_URL)
Session = async_sessionmaker(engine, expire_on_commit=False)


async def upsert_job(session, raw, dry_run: bool):
    from apps.api.models.job import Job  # import here to avoid circular

    content_hash = hashlib.sha256(raw.raw_text.encode()).hexdigest()

    result = await session.execute(
        sa.select(Job).where(
            Job.source_name == raw.source_name,
            Job.source_job_id == raw.source_job_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        if existing.content_hash == content_hash:
            return "skip"
        # Content changed (corrigendum) — re-extract
        existing.content_hash = content_hash
        existing.raw_text = raw.raw_text
        existing.status = "pending_extraction"
        if not dry_run:
            await session.commit()
        return "updated"

    job = Job(
        source_name=raw.source_name,
        source_job_id=raw.source_job_id,
        title=raw.title,
        organization=raw.organization,
        raw_text=raw.raw_text,
        content_hash=content_hash,
        apply_url=raw.apply_url,
        status="pending_extraction",
    )
    if not dry_run:
        session.add(job)
        await session.commit()
    return "new"


async def run_extraction(session, dry_run: bool):
    from apps.api.models.job import Job

    result = await session.execute(
        sa.select(Job).where(Job.status == "pending_extraction").limit(100)
    )
    jobs = result.scalars().all()
    print(f"[Pipeline] Extracting criteria for {len(jobs)} jobs...")

    for job in jobs:
        criteria = extract_criteria(job.raw_text or "")
        if criteria:
            job.criteria = criteria.model_dump()
            job.status = "active"
        else:
            job.status = "extraction_failed"
        if not dry_run:
            await session.commit()
        print(f"  {'[dry]' if dry_run else ''} {job.title[:60]} → {job.status}")


async def main(source_filter: str | None, dry_run: bool):
    scrapers = [S() for S in ALL_SCRAPERS
                if source_filter is None or S.source_name == source_filter]

    async with Session() as session:
        for scraper in scrapers:
            print(f"\n[Pipeline] Scraping {scraper.source_name}...")
            listings = scraper.fetch_listings()
            print(f"  Found {len(listings)} listings")
            counts = {"new": 0, "updated": 0, "skip": 0}
            for raw in listings:
                status = await upsert_job(session, raw, dry_run)
                counts[status] += 1
            print(f"  new={counts['new']} updated={counts['updated']} skip={counts['skip']}")

        if not dry_run:
            await run_extraction(session, dry_run)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.source, args.dry_run))
