"""Fetch remote jobs from free public APIs into docs/jobs.json.

Stdlib only. Run once a day (GitHub Actions does this). Each source fails on
its own; if every source fails, the old jobs.json is kept untouched.
"""

import json
import os
import sys
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "jobs.json")
MAX_AGE_DAYS = 30
UA = "Roamline/1.0 (personal job search)"


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def iso(ts):
    """Unix seconds -> ISO date string, or None."""
    if not isinstance(ts, (int, float)) or ts <= 0:
        return None
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def salary(lo, hi, currency=""):
    lo, hi = lo or 0, hi or 0
    if not lo and not hi:
        return ""
    cur = f"{currency} " if currency else "$"
    if lo and hi:
        return f"{cur}{int(lo):,}-{int(hi):,}"
    return f"{cur}{int(lo or hi):,}"


def safe_url(u):
    return u if isinstance(u, str) and u.startswith("https://") else ""


def job(source, title, company, location, tags, pay, url, posted):
    return {
        "title": (title or "").strip(),
        "company": (company or "").strip(),
        "location": (location or "").strip() or "Anywhere",
        "tags": [t for t in (tags or []) if isinstance(t, str)][:6],
        "salary": pay,
        "url": safe_url(url),
        "source": source,
        "posted": posted,
    }


# --- one normalizer per source; field names checked against each API's live response ---

def from_remoteok(data):
    # First element is RemoteOK's legal notice, not a job.
    return [
        job("Remote OK", j.get("position"), j.get("company"), j.get("location"), j.get("tags"),
            salary(j.get("salary_min"), j.get("salary_max")), j.get("url"), iso(j.get("epoch")))
        for j in data if isinstance(j, dict) and "position" in j
    ]


def from_remotive(data):
    return [
        job("Remotive", j.get("title"), j.get("company_name"), j.get("candidate_required_location"),
            [j.get("category")] if j.get("category") else [], j.get("salary") or "", j.get("url"),
            j.get("publication_date"))
        for j in data.get("jobs", [])
    ]


def from_himalayas(data):
    return [
        job("Himalayas", j.get("title"), j.get("companyName"),
            ", ".join(j.get("locationRestrictions") or []), j.get("categories"),
            salary(j.get("minSalary"), j.get("maxSalary"), j.get("currency") or ""),
            j.get("applicationLink") or j.get("guid"), iso(j.get("pubDate")))
        for j in data.get("jobs", [])
    ]


def from_arbeitnow(data):
    return [
        job("Arbeitnow", j.get("title"), j.get("company_name"), j.get("location"), j.get("tags"),
            "", j.get("url"), iso(j.get("created_at")))
        for j in data.get("data", []) if j.get("remote") is True
    ]


SOURCES = [
    ("https://remoteok.com/api", from_remoteok),
    ("https://remotive.com/api/remote-jobs", from_remotive),
    ("https://himalayas.app/jobs/api?limit=100", from_himalayas),
    ("https://www.arbeitnow.com/api/job-board-api", from_arbeitnow),
]


def clean(jobs, now=None):
    """Drop broken/old rows, dedupe by title+company, newest first."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    seen, out = set(), []
    for j in jobs:
        if not j["title"] or not j["url"] or not j["posted"]:
            continue
        try:
            posted = datetime.fromisoformat(j["posted"])
        except ValueError:
            continue
        if posted.tzinfo is None:  # Remotive dates have no zone; they're UTC.
            posted = posted.replace(tzinfo=timezone.utc)
        if posted < cutoff:
            continue
        if j["source"] == "Remotive" and posted > now - timedelta(days=1):
            continue  # Remotive's terms: show their jobs with a 24h delay.
        key = (j["title"].lower(), j["company"].lower())
        if key in seen:
            continue
        seen.add(key)
        j["posted"] = posted.isoformat()
        out.append(j)
    return sorted(out, key=lambda j: j["posted"], reverse=True)


def main():
    jobs, ok = [], 0
    for url, parse in SOURCES:
        try:
            got = parse(get_json(url))
            jobs += got
            ok += 1
            print(f"{url}: {len(got)} jobs")
        except Exception as e:  # one bad source must not kill the run
            print(f"{url}: FAILED ({e})", file=sys.stderr)
    if ok == 0:
        sys.exit("every source failed; keeping the old jobs.json")

    jobs = clean(jobs)
    payload = {"updated": datetime.now(timezone.utc).isoformat(), "count": len(jobs), "jobs": jobs}
    # Atomic write: a crash mid-write never leaves a half-written file.
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(OUT), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, OUT)
    print(f"wrote {len(jobs)} jobs from {ok}/{len(SOURCES)} sources")


if __name__ == "__main__":
    main()
