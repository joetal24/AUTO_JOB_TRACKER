import sys

import pytest

import alerts as alerts_mod
import db
import scheduler
from scrapers import rss_sources, selenium_scraper

JOB = {
    "title": "Senior Python Dev",
    "company": "Acme",
    "location": "Remote",
    "url": "https://example.com/jobs/1",
    "category": "keyword",
    "source": "remoteok",
    "keyword": None,
}


def test_run_scrapes_and_dedups(tmp_path, monkeypatch):
    d = str(tmp_path / "t.db")
    calls = {"n": 0}

    def fake_fetch_all():
        calls["n"] += 1
        return [JOB]

    def fake_keywords(kws):
        return [dict(JOB, url="https://example.com/jobs/3", source="linkedin")]

    def fake_watched(urls):
        return [dict(JOB, url="https://example.com/jobs/2", source="watched",
                     category="watched")]

    monkeypatch.setattr(rss_sources, "fetch_all", fake_fetch_all)
    monkeypatch.setattr(selenium_scraper, "scrape_keywords", fake_keywords)
    monkeypatch.setattr(selenium_scraper, "scrape_watched", fake_watched)

    assert scheduler.run(d) == 3
    assert scheduler.run(d) == 0  # dedup: nothing new
    assert calls["n"] == 2
    assert len(db.list_jobs(d)) == 3


def test_relevant_filters_jobs():
    kws = ["python", "react"]
    assert scheduler._relevant(JOB, kws) is True
    assert scheduler._relevant(dict(JOB, title="Bartender"), kws) is False


def test_main_alerts_fresh_jobs(tmp_path, monkeypatch):
    d = str(tmp_path / "t.db")
    db.init_db(d)
    db.upsert_job(JOB, d)
    sent = []

    monkeypatch.setattr(scheduler, "run", lambda *a: 0)
    monkeypatch.setattr(sys, "argv", ["scheduler.py", "--db", d, "--alert"])
    monkeypatch.setattr(alerts_mod, "send_alerts", lambda jobs: sent.append(jobs))
    scheduler.main()
    assert len(sent) == 1
    assert sent[0][0]["url"] == JOB["url"]
    assert db.get_setting("last_alert_at", None, d) is not None
