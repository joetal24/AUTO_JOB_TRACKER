import { useCallback, useEffect, useState } from "react";

const empty = { keyword: "", location: "", category: "", source: "", date_from: "", sort: "posted_at" };

function fmt(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString();
}

function JobsTable({ jobs }) {
  const dayAgo = Date.now() - 86400000;
  return (
    <table>
      <thead>
        <tr>
          <th>Title</th>
          <th>Company</th>
          <th>Location</th>
          <th>Salary</th>
          <th>Posted</th>
          <th>Category</th>
          <th>Source</th>
        </tr>
      </thead>
      <tbody>
        {jobs.map((j) => (
          <tr key={j.id || j.url}>
            <td>
              <a href={j.url} target="_blank" rel="noreferrer">{j.title}</a>
              {j.first_seen && Date.parse(j.first_seen) > dayAgo && <span className="new">new</span>}
            </td>
            <td>{j.company}</td>
            <td>{j.location}</td>
            <td>{j.salary}</td>
            <td>{fmt(j.posted_at)}</td>
            <td><span className={`tag tag-${j.category}`}>{j.category}</span></td>
            <td>{j.source}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function App() {
  const [tab, setTab] = useState("home");
  const [jobs, setJobs] = useState([]);
  const [stats, setStats] = useState(null);
  const [sources, setSources] = useState([]);
  const [watched, setWatched] = useState([]);
  const [filters, setFilters] = useState({ ...empty, category: "keyword" });
  const [url, setUrl] = useState("");
  const [label, setLabel] = useState("");
  const [running, setRunning] = useState(false);
  const [keywords, setKeywords] = useState("");
  const [kwSaved, setKwSaved] = useState(false);
  const [scrapeUrl, setScrapeUrl] = useState("");
  const [scraping, setScraping] = useState(false);
  const [pending, setPending] = useState(null);

  const load = useCallback(async () => {
    const q = new URLSearchParams(Object.entries(filters).filter(([, v]) => v));
    setJobs(await (await fetch(`/api/jobs?${q}`)).json());
    setStats(await (await fetch("/api/stats")).json());
    setSources(await (await fetch("/api/sources")).json());
    setWatched(await (await fetch("/api/watched")).json());
    const k = await (await fetch("/api/keywords")).json();
    setKeywords(k.keywords.join(", "));
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  const set = (k) => (e) => setFilters({ ...filters, [k]: e.target.value });

  const switchTab = (t) => {
    setTab(t);
    setFilters({ ...empty, category: t === "home" ? "keyword" : t === "watch" ? "watched" : "" });
  };

  const addWatched = async (e) => {
    e.preventDefault();
    if (!url) return;
    await fetch("/api/watched", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, label }),
    });
    setUrl("");
    setLabel("");
    load();
  };

  const saveKeywords = async (e) => {
    e.preventDefault();
    const list = keywords.split(",").map((s) => s.trim()).filter(Boolean);
    await fetch("/api/keywords", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keywords: list }),
    });
    setKwSaved(true);
    setTimeout(() => setKwSaved(false), 1500);
    load();
  };

  const runNow = async () => {
    setRunning(true);
    await fetch("/api/run", { method: "POST" });
    setRunning(false);
    load();
  };

  const runScrapeUrl = async (e) => {
    e.preventDefault();
    if (!scrapeUrl) return;
    setScraping(true);
    setPending(null);
    try {
      const r = await fetch("/api/scrape-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: scrapeUrl }),
      });
      if (r.ok) {
        const d = await r.json();
        setPending({ id: d.id, url: scrapeUrl, jobs: d.jobs });
      }
    } finally {
      setScraping(false);
    }
  };

  const savePending = async () => {
    await fetch(`/api/scrape-url/${pending.id}/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label: "" }),
    });
    setPending(null);
    setScrapeUrl("");
    load();
  };

  const discardPending = async () => {
    await fetch(`/api/scrape-url/${pending.id}/discard`, { method: "POST" });
    setPending(null);
  };

  return (
    <div className="app">
      <header>
        <div className="brand">
          <span className="logo">JT</span>
          <h1>Auto Job Tracker</h1>
        </div>
        <nav className="tabs">
          <button className={`tab${tab === "home" ? " on" : ""}`} onClick={() => switchTab("home")}>Home</button>
          <button className={`tab${tab === "watch" ? " on" : ""}`} onClick={() => switchTab("watch")}>Watch job</button>
          <button className={`tab${tab === "scrape" ? " on" : ""}`} onClick={() => switchTab("scrape")}>Scrape now</button>
        </nav>
        {stats && (
          <span className="stats">
            <span className="chip">{stats.total} offers</span>
            <span className="chip">{stats.watched_urls} watched</span>
          </span>
        )}
        <button className="btn primary" onClick={runNow} disabled={running}>
          {running ? "Scraping…" : "Run full scrape"}
        </button>
      </header>

      {tab === "home" && (
        <div className="layout">
          <aside>
            <form className="card" onSubmit={saveKeywords}>
              <h2>Keywords — tech / software</h2>
              <p className="hint">Auto-scraped listings are matched against these.</p>
              <textarea rows="5" value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                placeholder="python, react, devops, …" />
              <button type="submit" className="btn primary">
                {kwSaved ? "Saved ✓" : "Save keywords"}
              </button>
            </form>
          </aside>
          <div className="main">
            <form className="card">
              <h2>Filters</h2>
              <div className="grid">
                <input placeholder="Keyword" value={filters.keyword} onChange={set("keyword")} />
                <input placeholder="Location" value={filters.location} onChange={set("location")} />
                <input type="date" value={filters.date_from} onChange={set("date_from")} />
                <select value={filters.category} onChange={set("category")}>
                  <option value="">Category: all</option>
                  <option value="watched">watched</option>
                  <option value="keyword">keyword</option>
                </select>
                <select value={filters.source} onChange={set("source")}>
                  <option value="">Source: all</option>
                  {sources.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
                <select value={filters.sort} onChange={set("sort")}>
                  <option value="posted_at">Sort: posted date</option>
                  <option value="scraped_at">Sort: scraped date</option>
                </select>
              </div>
            </form>
            <div className="card">
              <h2>Auto-scraped offers ({jobs.length})</h2>
              <JobsTable jobs={jobs} />
              {jobs.length === 0 && <p className="hint">Nothing auto-scraped yet — run a full scrape or wait for the daily job.</p>}
            </div>
          </div>
        </div>
      )}

      {tab === "watch" && (
        <div className="layout">
          <aside>
            <form className="card" onSubmit={addWatched}>
              <h2>Watch a job board</h2>
              <p className="hint">Paste any job-listing URL — it gets scraped and filed under "watched".</p>
              <input placeholder="https://… job listing page"
                value={url} onChange={(e) => setUrl(e.target.value)} />
              <input placeholder="label, e.g. RemoteOK (optional)"
                value={label} onChange={(e) => setLabel(e.target.value)} />
              <button type="submit" className="btn primary">Add watched URL</button>
            </form>
            <div className="card">
              <h2>Watched sources ({watched.length})</h2>
              {watched.length === 0 ? (
                <p className="hint">Nothing watched yet.</p>
              ) : (
                <ul className="watched-list">
                  {watched.map((w) => (
                    <li key={w.id}>
                      <a href={w.url} target="_blank" rel="noreferrer">{w.label || w.url}</a>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </aside>
          <div className="main">
            <div className="card">
              <h2>Watched offers ({jobs.length})</h2>
              <JobsTable jobs={jobs} />
              {jobs.length === 0 && <p className="hint">Add a watched URL and run a scrape.</p>}
            </div>
          </div>
        </div>
      )}

      {tab === "scrape" && (
        <div className="scrape">
          <form className="card" onSubmit={runScrapeUrl}>
            <h2>Scrape a URL now</h2>
            <p className="hint">Paste any job-listing URL. The results appear below — then choose to keep it as a watched source or discard it.</p>
            <input placeholder="https://… job listing page"
              value={scrapeUrl} onChange={(e) => setScrapeUrl(e.target.value)} />
            <button type="submit" className="btn primary" disabled={scraping}>
              {scraping ? "Scraping…" : "Scrape"}
            </button>
          </form>

          {pending && (
            <div className="card">
              <h2>Scraped from {pending.url}</h2>
              <p className="hint">{pending.jobs.length} listing(s) found.</p>
              <JobsTable jobs={pending.jobs} />
              <div className="row">
                <button className="btn primary" onClick={savePending}>Keep — add to watched</button>
                <button className="btn ghost" onClick={discardPending}>Discard</button>
              </div>
            </div>
          )}
          {!pending && !scraping && <p className="hint">No scrape yet — enter a URL above.</p>}
        </div>
      )}
    </div>
  );
}
