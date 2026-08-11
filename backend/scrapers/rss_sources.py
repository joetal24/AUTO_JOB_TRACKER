"""RSS/JSON job sources — no browser, most recent, never blocked."""

import datetime as dt
import feedparser
import requests

SOURCES = {
    "remoteok": {
        "url": "https://remoteok.com/api",
        "kind": "json",
    },
    "weworkremotely": {
        "url": "https://weworkremotely.com/remote-jobs.rss",
        "kind": "rss",
    },
    "remotive": {
        "url": "https://remotive.com/api/remote-jobs",
        "kind": "json",
    },
}


def _job(title, company, location, url, salary, posted_at, source, keyword):
    return {
        "title": title,
        "company": company,
        "location": location or "Remote",
        "url": url,
        "salary": salary,
        "posted_at": posted_at,
        "category": "keyword",
        "source": source,
        "keyword": keyword,
    }


def fetch_remoteok():
    jobs = []
    for item in requests.get(SOURCES["remoteok"]["url"], timeout=20).json():
        if not isinstance(item, dict) or "position" not in item:
            continue
        salary = ""
        if item.get("salary_min") or item.get("salary_max"):
            lo = item.get("salary_min") or ""
            hi = item.get("salary_max") or ""
            salary = f"${lo} - ${hi}/yr"
        posted = item.get("date", "")
        if posted:
            posted = dt.datetime.fromisoformat(
                posted.replace("Z", "+00:00")
            ).isoformat(timespec="seconds")
        jobs.append(_job(
            item["position"], item.get("company"),
            item.get("location"), item.get("url"),
            salary, posted, "remoteok", None,
        ))
    return jobs


def fetch_weworkremotely():
    feed = feedparser.parse(SOURCES["weworkremotely"]["url"])
    jobs = []
    for e in feed.entries:
        # Title format: "Company: Job Title"
        parts = e.title.split(": ", 1)
        company = parts[0] if len(parts) == 2 else None
        title = parts[1] if len(parts) == 2 else e.title
        published = None
        if e.get("published_parsed"):
            published = dt.datetime(
                *e.published_parsed[:6], tzinfo=dt.timezone.utc
            ).isoformat(timespec="seconds")
        summary = e.get("summary", "")
        location = "Remote"
        for tag in ("<p>", "</p>", "<br />", "<br>", "&nbsp;"):
            summary = summary.replace(tag, " ")
        for word in summary.split():
            if word.strip() and word[0].isupper():
                location = word.strip()
                break
        jobs.append(_job(
            title, company, location, e.link,
            None, published, "weworkremotely", None,
        ))
    return jobs


def fetch_remotive():
    data = requests.get(SOURCES["remotive"]["url"], timeout=20).json()
    jobs = []
    for item in data.get("jobs", []):
        posted = item.get("publication_date", "")
        if posted:
            posted = dt.datetime.fromisoformat(
                posted.replace("Z", "+00:00")
            ).isoformat(timespec="seconds")
        jobs.append(_job(
            item.get("title"), item.get("company_name"),
            item.get("candidate_required_location"), item.get("url"),
            item.get("salary"), posted, "remotive", None,
        ))
    return jobs


FETCHERS = {
    "remoteok": fetch_remoteok,
    "weworkremotely": fetch_weworkremotely,
    "remotive": fetch_remotive,
}


def fetch_all():
    """Fetch every RSS/API source. Returns list of job dicts."""
    jobs = []
    for name, fn in FETCHERS.items():
        try:
            jobs.extend(fn())
        except Exception:
            # one flaky feed must not kill the whole run
            continue
    return jobs
