"""Daily alerts: email digest (smtplib) + Telegram bot."""

import html
import os
import smtplib
from email.mime.text import MIMEText

import requests


def _jobs_html(jobs):
    rows = ""
    for j in jobs:
        rows += (
            f'<tr><td><a href="{html.escape(j["url"])}">'
            f'{html.escape(j["title"])}</a></td>'
            f"<td>{html.escape(j['company'] or '')}</td>"
            f"<td>{html.escape(j['location'] or '')}</td>"
            f"<td>{html.escape(j['posted_at'] or '')}</td></tr>"
        )
    return f"<table border='1' cellpadding='6'><tr><th>Title</th><th>Company</th><th>Location</th><th>Posted</th></tr>{rows}</table>"


def send_email(jobs):
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    sender = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    recipients = os.environ["ALERT_EMAIL"].split(",")
    msg = MIMEText(_jobs_html(jobs), "html")
    msg["Subject"] = f"Job Tracker: {len(jobs)} new offer(s)"
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    with smtplib.SMTP(smtp_host, smtp_port) as s:
        s.starttls()
        s.login(sender, password)
        s.sendmail(sender, recipients, msg.as_string())


def send_telegram(jobs):
    token = os.environ["TELEGRAM_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    lines = [f"<b>Job Tracker:</b> {len(jobs)} new offer(s)"]
    for j in jobs[:20]:
        lines.append(
            f"<a href='{html.escape(j['url'])}'>{html.escape(j['title'])}</a>"
            f" — {html.escape(j['company'] or '')} ({html.escape(j['location'] or 'Remote')})"
        )
    if len(jobs) > 20:
        lines.append(f"...and {len(jobs) - 20} more")
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": "\n".join(lines), "parse_mode": "HTML"},
        timeout=20,
    )


def send_alerts(jobs):
    """Send to all configured channels. Raises on missing env config."""
    if not jobs:
        return
    if os.environ.get("SMTP_HOST"):
        send_email(jobs)
    if os.environ.get("TELEGRAM_TOKEN"):
        send_telegram(jobs)
