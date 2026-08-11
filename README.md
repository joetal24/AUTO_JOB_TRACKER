# Auto Job Tracker

Scrapes job offers into a SQLite DB and shows them in a React dashboard.
Two categories: **watched** (URLs you paste, scraped with Selenium) and
**keyword** (searches by keyword + location; RSS/API feeds first, LinkedIn
and Indeed via Selenium as best-effort). Keyword listings are matched
against a configurable **tech/software keyword list** (edit it in the
dashboard — defaults to Python, React, DevOps, …). Sends a daily digest of
new offers by email and/or Telegram.

```
backend/   Python: FastAPI (API + serves built dashboard) + scrapers + scheduler
frontend/  React (Vite) dashboard
```

## Quick start

Requires: Python 3.10+, Node 18+, [uv](https://docs.astral.sh/uv/),
[pnpm](https://pnpm.io/installation) (or corepack), and a Chrome/Chromium for
Selenium.

```bash
# backend deps (uv manages a .venv) — from the repo root
cd backend
uv sync
uv run pytest tests          # 19 tests

# frontend deps — from the repo root
cd frontend
pnpm install
```

## Running the frontend

The frontend is a Vite + React SPA. The backend (FastAPI) always needs to be
running first — it's the API that serves the job data.

**Prod mode (default):** build once, then FastAPI serves the compiled
dashboard on the same port as the API (no separate server, no CORS).

```bash
# from the repo root
cd frontend
pnpm build                   # outputs frontend/dist

cd ../backend
uv run uvicorn app:app --host 0.0.0.0 --port 8000
# open http://localhost:8000
```

**Dev mode (hot reload for frontend work):** run Vite's dev server; it
proxies `/api` to the backend on port 8000.

```bash
# terminal 1 — from the repo root
cd backend
uv run uvicorn app:app --port 8000

# terminal 2 — from the repo root
cd frontend
pnpm dev                     # open http://localhost:5173
```

## Alerts config

Copy `backend/.env.example` to `backend/.env` and fill in SMTP and/or
Telegram values. Omit `SMTP_HOST` to skip email; omit `TELEGRAM_TOKEN` to
skip Telegram.

## Daily scrape + alerts (cron)

```bash
# every day at 08:00, scrape → dedup → alert on new offers
0 8 * * * cd /path/to/Auto\ Jobtracker/backend && export $(grep -v '^#' .env | xargs) && uv run python scheduler.py --alert >> /tmp/jobtracker.log 2>&1
```

Test a run without alerts:

```bash
cd backend && uv run python scheduler.py
```

## Manual scrape from the dashboard

Click **Scrape now** — it calls `POST /api/run`. Or add a watched URL with
the form; the scheduler will scrape it on the next run.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/jobs?keyword=&location=&category=&source=&date_from=&sort=` | filtered offers |
| GET | `/api/stats` | totals by source |
| GET | `/api/sources` | distinct source names |
| GET | `/api/watched` | watched URLs |
| POST | `/api/watched` `{url, label}` | add a watched URL |
| GET | `/api/keywords` | tech/software keywords |
| POST | `/api/keywords` `{keywords: [...]}` | set keywords |
| POST | `/api/run` | run the full scheduled scrape |
| POST | `/api/scrape-url` `{url}` | scrape one URL now; returns `{id, jobs}` |
| POST | `/api/scrape-url/{id}/save` `{label}` | keep result + save URL to watched |
| POST | `/api/scrape-url/{id}/discard` | discard the pending scrape |

The dashboard has three tabs: **Home** (auto-scraped keyword listings from
the default RSS sites), **Watch job** (add/see watched URLs and their
offers), and **Scrape now** (paste a URL → review results → keep as watched
or discard).

## Deploying

Not suited to serverless (Leapcell/Render free tier sleeps; a Selenium cron
needs a live box). Use a small VPS — Hetzner CX22 (~€4/mo) or Oracle free
tier. One command on the box (Ubuntu) installs everything: Chrome, uv,
Node, the API + daily-scrape systemd timer:

```bash
git clone <this repo> /tmp/jobtracker
cd /tmp/jobtracker
bash deploy/deploy.sh            # installs to /opt/jobtracker
# then fill /opt/jobtracker/backend/.env and: systemctl restart jobtracker-api
```

Manual systemd instead of the script (cron for the daily job):

```ini
# /etc/systemd/system/jobtracker-scrape.service
[Unit]
Description=Daily job scrape + alerts
[Service]
WorkingDirectory=/path/to/Auto Jobtracker/backend
EnvironmentFile=/path/to/Auto Jobtracker/backend/.env
ExecStart=/usr/local/bin/uv run python scheduler.py --alert
```
plus a `[Timer]` unit (`OnCalendar=*-*-* 08:00:00`), and a `uvicorn` service
for the API. Build the frontend once on the box; `frontend/dist` is served
from FastAPI.

## Notes / known limits

- LinkedIn/Indeed Selenium scraping is best-effort: anti-bot walls may
  change. RSS feeds (RemoteOK, WeWorkRemotely, Remotive) are the stable core.
- Dedup is by job URL — a reposted offer with a new URL shows as new.
- The generic watched-page extractor looks for links with job-ish URLs and
  uses the anchor text as the title; messy pages may need per-site tweaks.
# AUTO_JOB_TRACKER
