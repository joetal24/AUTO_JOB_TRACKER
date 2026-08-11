from scrapers import selenium_scraper as ss


def test_card_to_job():
    text = "Senior Engineer\nAcme Corp\nRemote - Worldwide\n5 days ago"
    job = ss._card_to_job(text, "https://example.com/job/1",
                          "watched", "watched", None)
    assert job["title"] == "Senior Engineer"
    assert job["company"] == "Acme Corp"
    assert job["location"] == "Remote - Worldwide"
    assert job["category"] == "watched"
    assert job["posted_at"].startswith("2026-08-06")
    assert job["url"] == "https://example.com/job/1"


def test_card_to_job_short_text():
    assert ss._card_to_job("x", "https://example.com/job/1",
                           "watched", "watched", None) is None


def test_posted_at_relative():
    import datetime as dt

    for unit, days in (("day", 1), ("week", 7), ("month", 30)):
        p = ss._posted_at(f"Posted 2 {unit}s ago")
        expected = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days * 2)
        got = dt.datetime.fromisoformat(p)
        assert abs((got - expected).total_seconds()) < 60
    assert ss._posted_at("no date here") is None


def test_search_urls():
    assert "keywords=python" in ss.SEARCH_URLS["linkedin"].format(kw="python", loc="")
    assert "q=python" in ss.SEARCH_URLS["indeed"].format(kw="python", loc="Berlin")
