from scrapers import rss_sources


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_remoteok_parsing(monkeypatch):
    payload = [
        {"position": "Frontend Dev", "company": "X", "location": "Remote",
         "url": "https://remoteok.com/job/1", "salary_min": 90000,
         "salary_max": 120000, "date": "2026-08-01T00:00:00.000Z"},
        {"position": "Backend Dev", "company": "Y", "location": "Remote",
         "url": "https://remoteok.com/job/2"},
        "not a dict",
    ]
    monkeypatch.setattr(rss_sources.requests, "get",
                        lambda *a, **k: FakeResp(payload))
    jobs = rss_sources.fetch_remoteok()
    assert len(jobs) == 2
    assert jobs[0]["salary"] == "$90000 - $120000/yr"
    assert jobs[0]["posted_at"] == "2026-08-01T00:00:00+00:00"
    assert jobs[0]["category"] == "keyword" and jobs[0]["source"] == "remoteok"


def test_weworkremotely_parsing(monkeypatch):
    class Entry(dict):
        def __getattr__(self, k):
            return self[k]

    e = Entry(title="Acme: Platform Engineer", link="https://weworkremotely.com/jobs/1",
              published="Sat, 01 Aug 2026 00:00:00 +0000",
              summary="<p>Remote</p>  Company description")
    e["published_parsed"] = (2026, 8, 1, 0, 0, 0, 5, 213, 0)

    class Feed:
        entries = [e]

    monkeypatch.setattr(rss_sources.feedparser, "parse", lambda *a, **k: Feed())
    jobs = rss_sources.fetch_weworkremotely()
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Platform Engineer"
    assert jobs[0]["company"] == "Acme"
    assert jobs[0]["posted_at"].startswith("2026-08-01")


def test_fetch_all_isolates_bad_source(monkeypatch):
    def boom():
        raise RuntimeError("feed down")

    healthy = [JOB]

    monkeypatch.setitem(rss_sources.FETCHERS, "remoteok", boom)
    monkeypatch.setitem(rss_sources.FETCHERS, "weworkremotely", lambda: [JOB])
    monkeypatch.setitem(rss_sources.FETCHERS, "remotive", lambda: [JOB])
    assert rss_sources.fetch_all() == [JOB, JOB]


JOB = {
    "title": "t", "company": "c", "location": "Remote",
    "url": "https://example.com/j", "salary": None, "posted_at": None,
    "category": "keyword", "source": "x", "keyword": None,
}
