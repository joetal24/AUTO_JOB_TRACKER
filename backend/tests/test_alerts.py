import os

import alerts

JOB = {
    "title": "Backend Dev",
    "company": "Acme",
    "location": "Remote",
    "url": "https://example.com/jobs/1",
    "posted_at": "2026-08-01T00:00:00+00:00",
}


def test_jobs_html_links(monkeypatch):
    html = alerts._jobs_html([JOB])
    assert "example.com/jobs/1" in html
    assert "Backend Dev" in html


def test_send_telegram(monkeypatch):
    sent = {}

    def fake_post(url, **kw):
        sent["url"] = url
        sent["json"] = kw["json"]

    monkeypatch.setattr(alerts.requests, "post", fake_post)
    monkeypatch.setenv("TELEGRAM_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    alerts.send_telegram([JOB])
    assert "tok" in sent["url"]
    assert sent["json"]["chat_id"] == "42"
    assert "Backend Dev" in sent["json"]["text"]


def test_send_email(monkeypatch):
    class FakeSMTP:
        def __init__(self, host, port):
            self.host, self.port = host, port

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def starttls(self):
            pass

        def login(self, u, p):
            self.login_args = (u, p)

        def sendmail(self, frm, to, msg):
            self.send = (frm, to, msg)

    monkeypatch.setattr(alerts.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "u@test")
    monkeypatch.setenv("SMTP_PASSWORD", "pw")
    monkeypatch.setenv("ALERT_EMAIL", "a@test,b@test")
    alerts.send_email([JOB])
    assert os.environ["SMTP_HOST"] == "smtp.test"


def test_send_alerts_no_jobs_noop(monkeypatch):
    monkeypatch.setattr(alerts, "send_email", lambda *a: (_ for _ in ()).throw(AssertionError))
    monkeypatch.setattr(alerts, "send_telegram", lambda *a: (_ for _ in ()).throw(AssertionError))
    alerts.send_alerts([])
