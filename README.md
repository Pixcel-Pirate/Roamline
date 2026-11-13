# Roamline

A free, personal remote-job finder. No accounts, no payments, no tracking.

- `fetch_jobs.py` pulls jobs once a day from free public APIs (Remote OK, Remotive, Himalayas, Arbeitnow), drops anything older than 30 days or without an `https://` link, removes duplicates and writes `docs/jobs.json`. Python stdlib only.
- `docs/` is a static page (search, source and age filters, salary-only, saved jobs in your browser). It renders with `textContent`, never `innerHTML`, and has a strict Content-Security-Policy.
- `.github/workflows/update-jobs.yml` runs the tests and the fetcher daily and commits the new `jobs.json`.

## Set up (free)
1. Push this repo to GitHub.
2. Settings → Pages → Source: "Deploy from a branch", branch `main`, folder `/docs`.
3. Actions → "Update jobs" → Run workflow (it then runs daily by itself).

## Run locally
```
python3 -m unittest -v
python3 fetch_jobs.py
python3 -m http.server -d docs   # open http://localhost:8000
```

## Source terms
Each source asks to be credited and linked; the footer and every listing do that. Remotive also asks for at most 4 calls a day and a 24-hour delay on its jobs, which the fetcher follows. Don't use these feeds to collect sign-ups or emails.
