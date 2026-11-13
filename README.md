# Roamline

A free, personal remote-job finder. No accounts, no payments, no tracking.

- `fetch_jobs.py` pulls remote and hybrid jobs once a day from free sources: Remote OK, Remotive, Himalayas, Arbeitnow, Jobicy, The Muse, We Work Remotely, Adzuna and USAJOBS (with free keys), and public company career pages on Greenhouse, Lever and Ashby (listed in `companies.json`). It drops anything older than 30 days or without a safe link, removes duplicates and writes `docs/jobs.json`. Python stdlib only.
- `docs/` is a static page (search, source and age filters, salary-only, saved jobs in your browser). It renders with `textContent`, never `innerHTML`, and has a strict Content-Security-Policy.
- `.github/workflows/update-jobs.yml` runs the tests and the fetcher daily and commits the new `jobs.json`. `test.yml` runs the tests on every pull request, and Dependabot keeps the pinned actions updated.

## Set up (free)
1. Push this repo to GitHub.
2. Settings → Pages → Source: "Deploy from a branch", branch `main`, folder `/docs`.
3. Actions → "Update jobs" → Run workflow (it then runs daily by itself).

## Optional free keys (more jobs + local hybrid jobs)
Add these in **Settings → Secrets and variables → Actions**. Each one is optional; a source without its key is skipped.

| Name | Type | Where to get it |
| --- | --- | --- |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Secret | free sign-up at https://developer.adzuna.com |
| `USAJOBS_EMAIL`, `USAJOBS_KEY` | Secret | free request at https://developer.usajobs.gov |
| `SEARCH_ZIPS` | Variable | up to 10 ZIP codes, e.g. `30303,10001`, to pull extra hybrid jobs around them |
| `SEARCH_RADIUS_MILES` | Variable | default `30` |

On the page, "Hybrid near ZIP code" shows remote jobs plus hybrid jobs within the chosen distance. Hybrid jobs with map coordinates (Adzuna) are matched by distance; others by city and state name.

## Add more companies
Put the company's board name in `companies.json` (the part after `boards.greenhouse.io/`, `jobs.lever.co/` or `jobs.ashbyhq.com/`). A board that doesn't exist just shows as FAILED in the run log.

## Run locally
```
python3 -m unittest -v
python3 fetch_jobs.py
python3 -m http.server -d docs   # open http://localhost:8000
```

## Source terms
Each source asks to be credited and linked; the footer and every listing do that. Remotive also asks for at most 4 calls a day and a 24-hour delay on its jobs, and Adzuna asks for a linked "Adzuna" label of at least 116x23 px on its listings; the fetcher and page follow both. Don't use these feeds to collect sign-ups or emails.
