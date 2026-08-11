"""FastAPI backend: JSON API + serves the built React dashboard."""

import os
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db

db.init_db()

app = FastAPI(title="Auto Job Tracker")

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


class WatchedIn(BaseModel):
    url: str
    label: str | None = None


class KeywordsIn(BaseModel):
    keywords: list[str]


class ScrapeUrlIn(BaseModel):
    url: str


class ScrapeLabelIn(BaseModel):
    label: str | None = None


# One-off URL scrapes waiting for the user to keep or discard.
# ponytail: in-memory; lost on restart, fine for a short-lived decision.
PENDING = {}


@app.get("/api/jobs")
def jobs(keyword: str = None, location: str = None, category: str = None,
         source: str = None, date_from: str = None, sort: str = "posted_at"):
    rows = db.list_jobs(keyword=keyword, location=location, category=category,
                        source=source, date_from=date_from, sort=sort)
    return [dict(r) for r in rows]


@app.get("/api/stats")
def get_stats():
    return db.stats()


@app.get("/api/sources")
def sources():
    with db._conn() as c:
        rows = c.execute("SELECT DISTINCT source FROM jobs").fetchall()
    return [r["source"] for r in rows]


@app.get("/api/watched")
def watched():
    return [dict(r) for r in db.list_watched_urls()]


@app.post("/api/watched")
def add_watched(body: WatchedIn):
    if not body.url.startswith(("http://", "https://")):
        raise HTTPException(400, "url must start with http(s)://")
    db.add_watched_url(body.url, body.label)
    return {"ok": True}


@app.get("/api/keywords")
def get_keywords():
    return {"keywords": db.get_keywords()}


@app.post("/api/keywords")
def set_keywords(body: KeywordsIn):
    db.set_keywords([k.strip() for k in body.keywords if k.strip()])
    return {"keywords": db.get_keywords()}


@app.post("/api/run")
def run_now():
    import scheduler

    new = scheduler.run()
    return {"new": new}


@app.post("/api/scrape-url")
def scrape_url(body: ScrapeUrlIn):
    """Scrape one URL now; results are held until kept or discarded."""
    if not body.url.startswith(("http://", "https://")):
        raise HTTPException(400, "url must start with http(s)://")
    from scrapers import selenium_scraper

    jobs = selenium_scraper.scrape_page(body.url, "watched", "watched", None)
    sid = uuid.uuid4().hex[:12]
    PENDING[sid] = {"url": body.url, "jobs": jobs}
    return {"id": sid, "jobs": jobs}


@app.post("/api/scrape-url/{sid}/save")
def save_scrape(sid: str, body: ScrapeLabelIn | None = None):
    """Keep: add the URL to watched and persist the scraped jobs."""
    if sid not in PENDING:
        raise HTTPException(404, "scrape session not found")
    item = PENDING.pop(sid)
    db.add_watched_url(item["url"], body.label if body else None)
    n = sum(1 for j in item["jobs"] if db.upsert_job(j))
    return {"saved": n}


@app.post("/api/scrape-url/{sid}/discard")
def discard_scrape(sid: str):
    if sid not in PENDING:
        raise HTTPException(404, "scrape session not found")
    PENDING.pop(sid)
    return {"ok": True}


if DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(DIST / "index.html")
