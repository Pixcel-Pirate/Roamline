"""Fetch remote and hybrid jobs from free public sources into docs/jobs.json.

Stdlib only. Run once a day (GitHub Actions does this). Each source fails on
its own; if every source fails, or nothing usable comes back, the old
jobs.json is kept untouched.

Optional settings (environment variables, set as GitHub secrets/variables):
  ADZUNA_APP_ID, ADZUNA_APP_KEY   free key from developer.adzuna.com
  USAJOBS_EMAIL, USAJOBS_KEY      free key from developer.usajobs.gov
  SEARCH_ZIPS                     e.g. "10001,94103": extra local hybrid/remote search
  SEARCH_RADIUS_MILES             default 30
Sources without their key are skipped.
"""

import json
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "docs", "jobs.json")
COMPANIES = os.path.join(HERE, "companies.json")
MAX_AGE_DAYS = 30
MAX_JOBS = 15000
UA = "Roamline/1.0 (personal job search)"
MAX_BYTES = 30_000_000  # a sane API response is a few MB; refuse anything absurd
PAUSE = 0.5  # seconds between requests, to be polite to free APIs


def fetch(url, headers=None):
    time.sleep(PAUSE)
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError(f"response larger than {MAX_BYTES} bytes")
    return body


def get_json(url, headers=None):
    return json.loads(fetch(url, {"Accept": "application/json", **(headers or {})}))


# --- helpers: everything from an API is untrusted ---

def text(v, limit=200):
    """API value -> trimmed string. Anything that isn't a string becomes ''."""
    return v.strip()[:limit] if isinstance(v, str) else ""


def number(v):
    """Positive number from an int, float or numeric string, else 0."""
    if isinstance(v, bool):
        return 0
    if isinstance(v, str):
        try:
            v = float(v)
        except ValueError:
            return 0
    return v if isinstance(v, (int, float)) and 0 < v < 1e14 else 0


def coord(v, limit):
    if isinstance(v, bool) or not isinstance(v, (int, float, str)):
        return None
    try:
        v = float(v)
    except ValueError:
        return None
    return round(v, 4) if -limit <= v <= limit and v != 0 else None


def iso(ts):
    """Unix seconds -> ISO date string, or None."""
    if not number(ts):
        return None
    try:
        return datetime.fromtimestamp(number(ts), timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def rfc822(s):
    try:
        return parsedate_to_datetime(s).isoformat()
    except (TypeError, ValueError, IndexError):
        return None


def salary(lo, hi, currency="", period=""):
    lo, hi = number(lo), number(hi)
    if not lo and not hi:
        return ""
    cur = f"{text(currency, 5)} " if text(currency, 5) else "$"
    per = "/hr" if text(period, 20).lower() in ("hourly", "hour") else ""
    if lo and hi and lo != hi:
        return f"{cur}{int(lo):,}-{int(hi):,}{per}"
    return f"{cur}{int(lo or hi):,}{per}"


def safe_url(u):
    """Only https links survive (plain http is upgraded); javascript: and the rest are dropped."""
    if not isinstance(u, str) or len(u) >= 2000:
        return ""
    if u.startswith("http://"):
        u = "https://" + u[len("http://"):]
    return u if u.startswith("https://") else ""


def work_type(*texts, default=None):
    """'hybrid' or 'remote' if any text says so, else default."""
    blob = " ".join(text(t, 500) for t in texts).lower()
    if "hybrid" in blob:
        return "hybrid"
    if "remote" in blob or "anywhere" in blob:
        return "remote"
    return default


def job(source, title, company, location, tags, pay, url, posted, kind="remote", lat=None, lon=None):
    j = {
        "title": text(title),
        "company": text(company),
        "location": text(location) or ("Anywhere" if kind == "remote" else ""),
        "tags": [text(t, 40) for t in tags if text(t, 40)][:6] if isinstance(tags, list) else [],
        "salary": text(pay, 60),
        "url": safe_url(url),
        "source": source,
        "posted": posted if isinstance(posted, str) else None,
        "type": kind if kind in ("remote", "hybrid") else "remote",
    }
    lat, lon = coord(lat, 90), coord(lon, 180)
    if lat is not None and lon is not None:
        j["lat"], j["lon"] = lat, lon
    return j


# --- one parser per source; field names checked against each API's live response ---

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
            [j.get("category")], j.get("salary"), j.get("url"), j.get("publication_date"))
        for j in data.get("jobs", [])
    ]


def from_himalayas(data):
    return [
        job("Himalayas", j.get("title"), j.get("companyName"),
            ", ".join(map(text, j.get("locationRestrictions") or [])), j.get("categories"),
            salary(j.get("minSalary"), j.get("maxSalary"), j.get("currency"), j.get("salaryPeriod")),
            j.get("applicationLink") or j.get("guid"), iso(j.get("pubDate")))
        for j in data.get("jobs", [])
    ]


def from_arbeitnow(data):
    return [
        job("Arbeitnow", j.get("title"), j.get("company_name"), j.get("location"), j.get("tags"),
            "", j.get("url"), iso(j.get("created_at")))
        for j in data.get("data", []) if j.get("remote") is True
    ]


def from_jobicy(data):
    return [
        job("Jobicy", j.get("jobTitle"), j.get("companyName"), j.get("jobGeo"), j.get("jobIndustry"),
            salary(j.get("salaryMin"), j.get("salaryMax"), j.get("salaryCurrency"), j.get("salaryPeriod")),
            j.get("url"), j.get("pubDate"))
        for j in data.get("jobs", [])
    ]


def from_wwr(xml_bytes):
    # ponytail: stdlib XML parser; modern expat blocks entity-expansion bombs.
    out = []
    for item in ET.fromstring(xml_bytes).iter("item"):
        company, _, title = (item.findtext("title") or "").partition(": ")
        if not title:
            company, title = "", company
        out.append(job("We Work Remotely", title, company, item.findtext("region"),
                       [item.findtext("category")], "", item.findtext("link"),
                       rfc822(item.findtext("pubDate"))))
    return out


def from_adzuna(data, default_kind):
    out = []
    for j in data.get("results", []):
        kind = work_type(j.get("title"), j.get("description"), default=default_kind)
        out.append(job("Adzuna", j.get("title"), (j.get("company") or {}).get("display_name"),
                       (j.get("location") or {}).get("display_name"), [], salary(j.get("salary_min"), j.get("salary_max")),
                       j.get("redirect_url"), j.get("created"), kind, j.get("latitude"), j.get("longitude")))
    return out


def from_usajobs(data):
    out = []
    for item in (data.get("SearchResult") or {}).get("SearchResultItems", []):
        d = item.get("MatchedObjectDescriptor") or {}
        pay = (d.get("PositionRemuneration") or [{}])[0]
        locs = d.get("PositionLocation") or [{}]
        out.append(job("USAJOBS", d.get("PositionTitle"), d.get("OrganizationName"),
                       "; ".join(text(l.get("LocationName")) for l in locs[:3] if isinstance(l, dict)),
                       [], salary(pay.get("MinimumRange"), pay.get("MaximumRange")), d.get("PositionURI"),
                       d.get("PublicationStartDate")))
    return out


def from_greenhouse(slug, data):
    out = []
    for j in data.get("jobs", []):
        loc = (j.get("location") or {}).get("name")
        kind = work_type(loc, j.get("title"))
        if kind:
            out.append(job("Company sites", j.get("title"), j.get("company_name") or slug, loc, [], "",
                           j.get("absolute_url"), j.get("first_published") or j.get("updated_at"), kind))
    return out


def from_lever(slug, data):
    out = []
    for j in data if isinstance(data, list) else []:
        cats = j.get("categories") or {}
        kind = work_type(j.get("workplaceType"), cats.get("location"))
        if kind:
            out.append(job("Company sites", j.get("text"), slug.replace("-", " ").title(), cats.get("location"),
                           [cats.get("team")], "", j.get("hostedUrl"), iso(number(j.get("createdAt")) / 1000), kind))
    return out


def from_ashby(slug, data):
    out = []
    for j in data.get("jobs", []):
        kind = work_type(j.get("workplaceType"), j.get("location"), "remote" if j.get("isRemote") is True else "")
        if kind:
            out.append(job("Company sites", j.get("title"), slug.replace("-", " ").title(), j.get("location"),
                           [j.get("department")], "", j.get("jobUrl"), j.get("publishedAt"), kind))
    return out


# --- sources: each returns a list of jobs; pages are capped so a run stays small ---

def settings(env=None):
    env = os.environ if env is None else env
    zips = [z for z in re.split(r"[\s,]+", env.get("SEARCH_ZIPS", "")) if re.fullmatch(r"\d{5}", z)][:10]
    try:
        radius = int(env.get("SEARCH_RADIUS_MILES") or 30)
    except ValueError:
        radius = 30
    return zips, min(max(radius, 5), 100)


def src_simple(url, parse):
    return lambda: parse(get_json(url))


def src_cursor(base, parse, pages):
    """Himalayas and Jobicy page with ?cursor=<nextCursor>."""
    def run():
        out, cursor = [], None
        for _ in range(pages):
            data = get_json(base + (f"&cursor={urllib.parse.quote(cursor)}" if cursor else ""))
            out += parse(data)
            cursor = data.get("nextCursor")
            if not cursor or data.get("hasMore") is False:
                break
        return out
    return run


def src_wwr():
    return from_wwr(fetch("https://weworkremotely.com/remote-jobs.rss", {"Accept": "application/rss+xml"}))


def src_adzuna():
    app_id, key = os.environ.get("ADZUNA_APP_ID"), os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not key:
        return None
    zips, radius = settings()
    searches = [("remote", None, 10), ("hybrid", None, 5)]
    searches += [(what, z, 2) for z in zips for what in ("remote", "hybrid")]
    out = []
    for what, where, pages in searches:
        for page in range(1, pages + 1):
            q = {"app_id": app_id, "app_key": key, "results_per_page": 50, "what": what,
                 "max_days_old": MAX_AGE_DAYS, "content-type": "application/json"}
            if where:
                q.update(where=where, distance=round(radius * 1.609))  # Adzuna wants km
            data = get_json(f"https://api.adzuna.com/v1/api/jobs/us/search/{page}?{urllib.parse.urlencode(q)}")
            got = from_adzuna(data, what)
            out += got
            if len(got) < 50:
                break
    return out


def src_usajobs():
    email, key = os.environ.get("USAJOBS_EMAIL"), os.environ.get("USAJOBS_KEY")
    if not email or not key:
        return None
    data = get_json("https://data.usajobs.gov/api/Search?RemoteIndicator=True&ResultsPerPage=500&DatePosted=30",
                    {"Host": "data.usajobs.gov", "User-Agent": email, "Authorization-Key": key})
    return from_usajobs(data)


def src_company_boards():
    try:
        with open(COMPANIES, encoding="utf-8") as f:
            boards = json.load(f)
    except FileNotFoundError:
        return None
    urls = {
        "greenhouse": ("https://boards-api.greenhouse.io/v1/boards/{}/jobs", from_greenhouse),
        "lever": ("https://api.lever.co/v0/postings/{}?mode=json", from_lever),
        "ashby": ("https://api.ashbyhq.com/posting-api/job-board/{}", from_ashby),
    }
    out = []
    for ats, (url, parse) in urls.items():
        for slug in boards.get(ats, []):
            if not re.fullmatch(r"[a-z0-9-]{1,60}", str(slug)):
                print(f"  {ats}/{slug}: skipped, bad name", file=sys.stderr)
                continue
            try:
                out += parse(slug, get_json(url.format(slug)))
            except Exception as e:  # one dead company board must not drop the rest
                print(f"  {ats}/{slug}: FAILED ({e})", file=sys.stderr)
    return out


SOURCES = [
    ("Remote OK", src_simple("https://remoteok.com/api", from_remoteok)),
    ("Remotive", src_simple("https://remotive.com/api/remote-jobs", from_remotive)),
    ("Himalayas", src_cursor("https://himalayas.app/jobs/api?limit=20", from_himalayas, 15)),
    ("Arbeitnow", src_simple("https://www.arbeitnow.com/api/job-board-api", from_arbeitnow)),
    ("Jobicy", src_cursor("https://jobicy.com/api/jobs?count=100", from_jobicy, 5)),
    ("We Work Remotely", src_wwr),
    ("Adzuna", src_adzuna),
    ("USAJOBS", src_usajobs),
    ("Company sites", src_company_boards),
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
        except (TypeError, ValueError):
            continue
        if posted.tzinfo is None:  # Remotive/USAJOBS dates have no zone; treat as UTC.
            posted = posted.replace(tzinfo=timezone.utc)
        if posted < cutoff or posted > now + timedelta(days=1):
            continue
        if j["source"] == "Remotive" and posted > now - timedelta(days=1):
            continue  # Remotive's terms: show their jobs with a 24h delay.
        key = (j["title"].lower(), j["company"].lower())
        if key in seen:
            continue
        seen.add(key)
        j["posted"] = posted.isoformat()
        out.append(j)
    return sorted(out, key=lambda j: j["posted"], reverse=True)[:MAX_JOBS]


def main():
    jobs, ok, tried = [], 0, 0
    for name, run in SOURCES:
        try:
            got = run()
        except Exception as e:  # one bad source must not kill the run
            tried += 1
            print(f"{name}: FAILED ({e})", file=sys.stderr)
            continue
        if got is None:
            print(f"{name}: skipped (no key or config)")
            continue
        tried += 1
        ok += 1
        jobs += got
        print(f"{name}: {len(got)} jobs")
    if ok == 0:
        sys.exit("every source failed; keeping the old jobs.json")

    jobs = clean(jobs)
    if not jobs:  # sources answered but nothing usable: likely an API change
        sys.exit("no usable jobs after cleaning; keeping the old jobs.json")
    payload = {"updated": datetime.now(timezone.utc).isoformat(), "count": len(jobs), "jobs": jobs}
    # Atomic write: a crash mid-write never leaves a half-written file.
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(OUT), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, OUT)
    print(f"wrote {len(jobs)} jobs from {ok}/{tried} sources")


if __name__ == "__main__":
    main()
