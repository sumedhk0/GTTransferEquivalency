# GT Transfer Equivalencies

Static website + nightly scraper that mirrors Georgia Tech's transfer equivalency table and lets you filter by GT course, external school, US state, or community-college status.

- **Site**: `site/` — plain HTML/JS/CSS, deployed to GitHub Pages.
- **Scraper**: `scraper/` — Python, runs nightly via GitHub Actions, writes `site/data.json`.
- **CLI** (still works): `python -m scraper.reverse_transfer APPH 1040 --state CA --community-college`

## One-time repo setup

1. **Get a College Scorecard API key** (free): https://api.data.gov/signup/
2. In the GitHub repo → Settings → Secrets and variables → Actions → add secret:
   - `COLLEGE_SCORECARD_API_KEY` = your key
3. Settings → Pages → Source: **GitHub Actions**.
4. Trigger the first scrape: Actions → **Nightly scrape** → Run workflow.
5. After it finishes, the **Deploy site** workflow runs automatically and publishes the page.

## Local dev

```bash
pip install -r scraper/requirements.txt

# Full scrape (~30 min)
export COLLEGE_SCORECARD_API_KEY=...
python -m scraper.scrape

# Preview the site
python -m http.server -d site 8000
# open http://localhost:8000
```

## Data format (`site/data.json`)

```json
{
  "generated_at": "2026-04-15T04:07:12Z",
  "schools": [
    {
      "code": "001569",
      "name": "De Anza College",
      "state": "CA",
      "is_community_college": true,
      "courses": [
        {"ext_subj":"BIOL","ext_num":"10","ext_title":"Intro Biology",
         "gt_subj":"BIOL","gt_num":"1510","gt_credits":"3"}
      ]
    }
  ]
}
```
