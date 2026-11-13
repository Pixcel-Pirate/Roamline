<div align="center">

# Roamline

**A free, personal remote-job finder.**

No accounts, no payments, no tracking. Fresh remote and hybrid jobs from free public feeds, updated every day.

<a href="https://github.com/Pixcel-Pirate/Roamline/actions/workflows/update-jobs.yml"><img alt="Update jobs" src="https://github.com/Pixcel-Pirate/Roamline/actions/workflows/update-jobs.yml/badge.svg"></a>
<a href="https://github.com/Pixcel-Pirate/Roamline/actions/workflows/test.yml"><img alt="Tests" src="https://github.com/Pixcel-Pirate/Roamline/actions/workflows/test.yml/badge.svg"></a>
<a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-yellow"></a>
<a href="https://buymeacoffee.com/saucie83g"><img alt="Buy Me a Coffee" src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-FFDD00?logo=buymeacoffee&logoColor=black"></a>
<img alt="Python" src="https://img.shields.io/badge/Python-stdlib%20only-3776AB?logo=python&logoColor=white">
<img alt="GitHub Pages" src="https://img.shields.io/badge/GitHub%20Pages-static-222222?logo=githubpages&logoColor=white">
<a href="https://github.com/Pixcel-Pirate/Roamline/commits/main"><img alt="Last commit" src="https://img.shields.io/github/last-commit/Pixcel-Pirate/Roamline"></a>

<br><br>

<a href="https://buymeacoffee.com/saucie83g"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" height="48"></a>

[How it works](#how-it-works) · [Set up (free)](#set-up-free) · [Free keys](#optional-free-keys-more-jobs--local-hybrid-jobs) · [Add companies](#add-more-companies) · [Run locally](#run-locally) · [Source terms](#source-terms) · [License](#license)

</div>

---

## How it works

- `fetch_jobs.py` pulls remote and hybrid jobs once a day from free sources: Remote OK, Remotive, Himalayas, Arbeitnow, Jobicy, We Work Remotely, Adzuna and USAJOBS (with free keys), and public company career pages on Greenhouse, Lever and Ashby (listed in `companies.json`). It drops anything older than 30 days or without a safe link, removes duplicates and writes `docs/jobs.json`. Python stdlib only.
- `docs/` is a static page (search, source and age filters, salary-only, saved jobs in your browser). It renders with `textContent`, never `innerHTML`, and has a strict Content-Security-Policy.
- `.github/workflows/update-jobs.yml` runs the tests and the fetcher daily and deploys the page to GitHub Pages. `test.yml` runs the tests on every pull request, and Dependabot keeps the pinned actions updated.

## Set up (free)
1. Settings → Pages → Build and deployment → Source: **GitHub Actions**.
2. Actions → "Update jobs" → Run workflow. It then runs daily and on every push to `main`.

The workflow builds `docs/` with fresh jobs and deploys it to Pages directly; it never commits to `main`, so `main` can be protected by a ruleset. `docs/jobs.json` in the repo is only sample data for running locally.

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

## License

[MIT](LICENSE) © 2026 Pixcel. If Roamline helps you land something, you can [buy me a coffee](https://buymeacoffee.com/saucie83g).
