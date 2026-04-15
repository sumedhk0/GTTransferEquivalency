# Setup: running your own copy

## One-time repo setup

1. **Fork / clone the repo.**
2. **Get a College Scorecard API key** (free): https://api.data.gov/signup/
3. On GitHub → Settings → Secrets and variables → Actions → New secret:
   - `COLLEGE_SCORECARD_API_KEY` = your key
4. Settings → Pages → Source: **GitHub Actions**.
5. Actions tab → **Nightly scrape** → **Run workflow** to seed `site/data.json`.
6. When the scrape finishes, **Deploy site** runs automatically and publishes the page.

## Local development

```bash
pip install -r scraper/requirements.txt

# Full scrape (~30 min). --state/--community-college on the CLI also use this key.
export COLLEGE_SCORECARD_API_KEY=...
python -m scraper.scrape

# Preview the site at http://localhost:8000
python -m http.server -d site 8000
```

Tip: to iterate on the site without waiting on a full scrape, temporarily set `LETTERS = ["A"]` in `scraper/reverse_transfer.py` so you get a small `data.json` in a minute or two.

## How it's wired

- `.github/workflows/scrape.yml` — cron at 04:00 UTC, runs `scraper/scrape.py`, commits `site/data.json` if it changed.
- `.github/workflows/pages.yml` — on any push touching `site/`, deploys to GitHub Pages.
- `scraper/scrape.py` — orchestrator; reuses functions from `scraper/reverse_transfer.py`.
- `site/app.js` — fetches `data.json` once, filters client-side.
