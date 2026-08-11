"""Selenium scraper: generic watched URLs + LinkedIn/Indeed keyword search.

Best-effort heuristic extraction — job boards vary. Link href is the
dedup key; card text is parsed into title/company/location/date.
"""

import os
import re
import time

from selenium import webdriver
from selenium.webdriver.common.by import By

JOB_HREF_RE = re.compile(r"(job|position|listing|offer|career)", re.I)
REL_DATE_RE = re.compile(r"(\d+)\s*(day|hour|week|month)s?\s*ago", re.I)
LOC_HINT_RE = re.compile(r"(remote|hybrid|on[- ]?site)", re.I)

SEARCH_URLS = {
    "linkedin": "https://www.linkedin.com/jobs/search/?keywords={kw}&location={loc}",
    "indeed": "https://www.indeed.com/jobs?q={kw}&l={loc}",
}


def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,2000")
    chrome_bin = os.environ.get("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
    return webdriver.Chrome(options=options)


def _posted_at(text):
    m = REL_DATE_RE.search(text)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)
    days = {"day": n, "hour": 0, "week": n * 7, "month": n * 30}[unit]
    import datetime as dt

    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).isoformat(
        timespec="seconds"
    )


def _card_to_job(text, href, category, source, keyword):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) < 1 or not (3 <= len(lines[0]) <= 120):
        return None
    title = lines[0]
    company = lines[1] if len(lines) > 1 else None
    location = None
    for line in lines[1:]:
        if LOC_HINT_RE.search(line) or (company and line != company and "," in line):
            location = line
            break
    return {
        "title": title,
        "company": company,
        "location": location,
        "url": href,
        "salary": None,
        "posted_at": _posted_at(text),
        "category": category,
        "source": source,
        "keyword": keyword,
    }


def scrape_page(url, category, source, keyword=None, driver=None):
    """Load one page and extract job listings. Returns list of job dicts."""
    own = driver is None
    driver = driver or get_driver()
    try:
        driver.get(url)
        time.sleep(3)
        anchors = driver.find_elements(By.TAG_NAME, "a")
        best = {}
        for a in anchors:
            try:
                href = a.get_attribute("href") or ""
                text = a.text.strip()
            except Exception:
                continue
            if not JOB_HREF_RE.search(href) or not (3 <= len(text) <= 120):
                continue
            # keep the anchor with the richest text per href
            if href not in best or len(text) > len(best[href]):
                best[href] = text
        jobs = []
        for href, text in best.items():
            job = _card_to_job(text, href, category, source, keyword)
            if job:
                jobs.append(job)
        return jobs
    finally:
        if own and driver:
            driver.quit()


def scrape_watched(watched_urls):
    """Scrape all active watched URLs. Returns list of job dicts."""
    jobs = []
    for row in watched_urls:
        jobs.extend(scrape_page(row["url"], "watched", "watched", row.get("label")))
    return jobs


def scrape_keywords(keywords, locations=("",), sources=("linkedin", "indeed")):
    """Run keyword+location searches across LinkedIn/Indeed. Best-effort."""
    jobs = []
    for src in sources:
        for kw in keywords:
            for loc in locations:
                url = SEARCH_URLS[src].format(
                    kw=kw.replace(" ", "+"), loc=loc.replace(" ", "+")
                )
                try:
                    jobs.extend(scrape_page(url, "keyword", src, kw))
                except Exception:
                    continue
    return jobs
