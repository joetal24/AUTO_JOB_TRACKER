import app
import db
from fastapi.testclient import TestClient
from scrapers import selenium_scraper

JOB = {
    "title": "Senior Python Dev",
    "company": "Acme",
    "location": "Remote",
    "url": "https://example.com/jobs/1",
    "salary": None,
    "posted_at": None,
    "category": "watched",
    "source": "watched",
    "keyword": None,
}


def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "t.db"))
    db.init_db()
    monkeypatch.setattr(
        selenium_scraper, "scrape_page",
        lambda url, cat, src, kw: [dict(JOB, url=url)],
    )
    return TestClient(app.app)


def test_scrape_url_then_save(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    r = client.post("/api/scrape-url", json={"url": "https://x.com/jobs"})
    assert r.status_code == 200
    sid = r.json()["id"]
    assert len(r.json()["jobs"]) == 1
    assert db.list_jobs() == []  # nothing persisted until kept

    r = client.post(f"/api/scrape-url/{sid}/save", json={"label": "X board"})
    assert r.json() == {"saved": 1}
    assert len(db.list_jobs()) == 1
    watched = db.list_watched_urls()
    assert watched[0]["url"] == "https://x.com/jobs"
    assert watched[0]["label"] == "X board"


def test_scrape_url_then_discard(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    sid = client.post("/api/scrape-url", json={"url": "https://x.com/jobs"}).json()["id"]
    r = client.post(f"/api/scrape-url/{sid}/discard")
    assert r.json() == {"ok": True}
    assert db.list_jobs() == []
    assert db.list_watched_urls() == []


def test_scrape_url_requires_http(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    r = client.post("/api/scrape-url", json={"url": "ftp://x.com"})
    assert r.status_code == 400


def test_save_unknown_session(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    assert client.post("/api/scrape-url/nope/save").status_code == 404
