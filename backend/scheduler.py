"""Cron entrypoint: scrape all sources → dedup into DB → alert new jobs."""

import argparse
import sys

import db
from scrapers import rss_sources, selenium_scraper


def _relevant(job, keywords):
    hay = f"{job['title']} {job.get('company') or ''}".lower()
    return any(k.lower() in hay for k in keywords)


def run(db_path=db.DB_PATH):
    """Scrape every source and insert new jobs. Returns count of new jobs."""
    db.init_db(db_path)
    keywords = db.get_keywords(db_path)
    new = 0
    for job in rss_sources.fetch_all():
        if not _relevant(job, keywords):
            continue
        if db.upsert_job(job, db_path):
            new += 1
    for job in selenium_scraper.scrape_keywords(keywords):
        if db.upsert_job(job, db_path):
            new += 1
    for job in selenium_scraper.scrape_watched(db.list_watched_urls(db_path)):
        if db.upsert_job(job, db_path):
            new += 1
    return new


def main():
    parser = argparse.ArgumentParser(description="Scrape job sources into the DB")
    parser.add_argument("--db", default=db.DB_PATH)
    parser.add_argument("--alert", action="store_true", help="send daily alerts")
    args = parser.parse_args()

    new = run(args.db)
    print(f"scraped: {new} new job(s)")
    if args.alert:
        last = db.get_setting("last_alert_at", None, args.db)
        fresh = db.jobs_since(last, args.db) if last else db.list_jobs(db_path=args.db)
        if fresh:
            import alerts

            alerts.send_alerts(fresh)
        db.set_setting("last_alert_at", db._now(), args.db)
        print(f"alerts sent for {len(fresh)} job(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
