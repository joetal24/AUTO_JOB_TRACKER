import pytest

import db

JOB = {
    "title": "Senior Python Dev",
    "company": "Acme",
    "location": "Remote",
    "url": "https://example.com/jobs/1",
    "salary": "$120k",
    "posted_at": "2026-08-01T00:00:00+00:00",
    "category": "keyword",
    "source": "remoteok",
    "keyword": None,
}


@pytest.fixture
def d(tmp_path):
    p = str(tmp_path / "test.db")
    db.init_db(p)
    return p


def test_upsert_dedup(d):
    assert db.upsert_job(JOB, d) is True
    assert db.upsert_job(JOB, d) is False
    rows = db.list_jobs(d)
    assert len(rows) == 1
    assert rows[0]["title"] == "Senior Python Dev"


def test_upsert_same_url_different_title_dedup(d):
    db.upsert_job(JOB, d)
    dup = dict(JOB, title="Changed Title")
    assert db.upsert_job(dup, d) is False


def test_filters(d):
    db.upsert_job(JOB, d)
    db.upsert_job({**JOB, "title": "DevOps Eng", "company": "Beta",
                   "location": "Berlin", "url": "https://example.com/jobs/2",
                   "category": "watched", "source": "watched"}, d)
    assert len(db.list_jobs(d)) == 2
    assert len(db.list_jobs(d, keyword="python")) == 1
    assert len(db.list_jobs(d, location="berlin")) == 1
    assert len(db.list_jobs(d, category="watched")) == 1
    assert len(db.list_jobs(d, source="remoteok")) == 1
    assert len(db.list_jobs(d, date_from="2026-01-01T00:00:00+00:00")) == 2


def test_watched_urls(d):
    db.add_watched_url("https://example.com/listings", "My board", d)
    db.add_watched_url("https://example.com/listings", "dup", d)
    rows = db.list_watched_urls(d)
    assert len(rows) == 1
    assert rows[0]["label"] == "My board"


def test_settings(d):
    assert db.get_setting("k", None, d) is None
    db.set_setting("k", "v", d)
    assert db.get_setting("k", None, d) == "v"
    db.set_setting("k", "w", d)
    assert db.get_setting("k", None, d) == "w"


def test_keywords(d):
    assert db.get_keywords(d) == db.DEFAULT_KEYWORDS
    db.set_keywords(["python", " react ", ""], d)
    assert db.get_keywords(d) == ["python", "react"]
    assert db.get_keywords(d)[0] == "python"


def test_jobs_since(d):
    db.upsert_job(JOB, d)
    rows = db.jobs_since("2999-01-01T00:00:00+00:00", d)
    assert len(rows) == 0
    rows = db.jobs_since("2000-01-01T00:00:00+00:00", d)
    assert len(rows) == 1
