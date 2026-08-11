import sqlite3
from datetime import datetime, timezone

DB_PATH = "jobs.db"

DEFAULT_KEYWORDS = [
    "python", "software", "developer", "engineer", "fullstack", "full stack",
    "devops", "backend", "frontend", "data", "ai", "machine learning",
    "react", "node", "cloud", "sre", "devsecops", "golang", "java",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    url TEXT NOT NULL UNIQUE,
    salary TEXT,
    posted_at TEXT,
    scraped_at TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('watched', 'keyword')),
    source TEXT NOT NULL,
    keyword TEXT,
    first_seen TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS watched_urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    label TEXT,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _conn(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path=None):
    db_path = db_path or DB_PATH
    with _conn(db_path) as c:
        c.executescript(SCHEMA)


def upsert_job(job, db_path=None):
    db_path = db_path or DB_PATH
    """Insert a job, dedup by url. Returns True if newly inserted."""
    now = _now()
    with _conn(db_path) as c:
        cur = c.execute(
            "SELECT id FROM jobs WHERE url = ?", (job["url"],)
        )
        if cur.fetchone():
            return False
        c.execute(
            """INSERT INTO jobs (title, company, location, url, salary,
               posted_at, scraped_at, category, source, keyword, first_seen)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                job["title"],
                job.get("company"),
                job.get("location"),
                job["url"],
                job.get("salary"),
                job.get("posted_at"),
                now,
                job["category"],
                job["source"],
                job.get("keyword"),
                now,
            ),
        )
    return True


def list_jobs(db_path=None, keyword=None, location=None, category=None,
              source=None, date_from=None, sort="posted_at"):
    """Filtered job list. Returns list of sqlite3.Row."""
    db_path = db_path or DB_PATH
    q = ["SELECT * FROM jobs"]
    where, args = [], []
    if keyword:
        like = f"%{keyword}%"
        where.append("(title LIKE ? OR company LIKE ? OR salary LIKE ?)")
        args += [like, like, like]
    if location:
        where.append("location LIKE ?")
        args.append(f"%{location}%")
    if category:
        where.append("category = ?")
        args.append(category)
    if source:
        where.append("source = ?")
        args.append(source)
    if date_from:
        where.append("first_seen >= ?")
        args.append(date_from)
    if where:
        q.append("WHERE " + " AND ".join(where))
    col = "posted_at" if sort == "posted_at" else "scraped_at"
    q.append(f"ORDER BY {col} DESC LIMIT 500")
    with _conn(db_path) as c:
        return c.execute(" ".join(q), args).fetchall()


def add_watched_url(url, label=None, db_path=None):
    db_path = db_path or DB_PATH
    with _conn(db_path) as c:
        c.execute(
            "INSERT OR IGNORE INTO watched_urls (url, label) VALUES (?, ?)",
            (url, label),
        )


def list_watched_urls(db_path=None, active_only=True):
    db_path = db_path or DB_PATH
    with _conn(db_path) as c:
        if active_only:
            return c.execute(
                "SELECT * FROM watched_urls WHERE active = 1"
            ).fetchall()
        return c.execute("SELECT * FROM watched_urls").fetchall()


def set_setting(key, value, db_path=None):
    db_path = db_path or DB_PATH
    with _conn(db_path) as c:
        c.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )


def get_setting(key, default=None, db_path=None):
    db_path = db_path or DB_PATH
    with _conn(db_path) as c:
        row = c.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else default


def get_keywords(db_path=None):
    db_path = db_path or DB_PATH
    raw = get_setting("keywords", None, db_path)
    if not raw:
        return DEFAULT_KEYWORDS
    return [k.strip() for k in raw.split(",") if k.strip()]


def set_keywords(keywords, db_path=None):
    db_path = db_path or DB_PATH
    set_setting("keywords", ",".join(keywords), db_path)


def jobs_since(ts, db_path=None):
    db_path = db_path or DB_PATH
    """Jobs first seen after ts (for daily alerts)."""
    with _conn(db_path) as c:
        return c.execute(
            "SELECT * FROM jobs WHERE first_seen > ? ORDER BY first_seen ASC",
            (ts,),
        ).fetchall()


def stats(db_path=None):
    db_path = db_path or DB_PATH
    with _conn(db_path) as c:
        total = c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        by_source = dict(
            c.execute(
                "SELECT source, COUNT(*) FROM jobs GROUP BY source"
            ).fetchall()
        )
        watched = c.execute(
            "SELECT COUNT(*) FROM watched_urls WHERE active = 1"
        ).fetchone()[0]
    return {"total": total, "by_source": by_source, "watched_urls": watched}
