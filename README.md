<div align="center">

# Roamline

**A free, personal remote-job finder.**

No accounts, no payments, no tracking. Fresh remote jobs from free public feeds, updated every day.

<a href="https://github.com/Pixcel-Pirate/Roamline/actions/workflows/update-jobs.yml"><img alt="Update jobs" src="https://github.com/Pixcel-Pirate/Roamline/actions/workflows/update-jobs.yml/badge.svg"></a>
<a href="https://github.com/Pixcel-Pirate/Roamline/actions/workflows/test.yml"><img alt="Tests" src="https://github.com/Pixcel-Pirate/Roamline/actions/workflows/test.yml/badge.svg"></a>
<a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-yellow"></a>
<a href="https://buymeacoffee.com/saucie83g"><img alt="Buy Me a Coffee" src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-FFDD00?logo=buymeacoffee&logoColor=black"></a>
<img alt="Python" src="https://img.shields.io/badge/Python-stdlib%20only-3776AB?logo=python&logoColor=white">
<img alt="GitHub Pages" src="https://img.shields.io/badge/GitHub%20Pages-static-222222?logo=githubpages&logoColor=white">
<a href="https://github.com/Pixcel-Pirate/Roamline/commits/main"><img alt="Last commit" src="https://img.shields.io/github/last-commit/Pixcel-Pirate/Roamline"></a>

<br><br>

<a href="https://buymeacoffee.com/saucie83g"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me a Coffee" height="48"></a>

[How it works](#how-it-works) · [Set up (free)](#set-up-free) · [Run locally](#run-locally) · [Source terms](#source-terms) · [License](#license)

</div>

---

## How it works

- `fetch_jobs.py` pulls jobs once a day from free public APIs (Remote OK, Remotive, Himalayas, Arbeitnow), drops anything older than 30 days or without an `https://` link, removes duplicates and writes `docs/jobs.json`. Python stdlib only.
- `docs/` is a static page (search, source and age filters, salary-only, saved jobs in your browser). It renders with `textContent`, never `innerHTML`, and has a strict Content-Security-Policy.
- `.github/workflows/update-jobs.yml` runs the tests and the fetcher daily and commits the new `jobs.json`. `test.yml` runs the tests on every pull request, and Dependabot keeps the pinned actions updated.

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

## License

[MIT](LICENSE) © 2026 Pixcel. If Roamline helps you land something, you can [buy me a coffee](https://buymeacoffee.com/saucie83g).
