# Opportunity Radar — Mobile Web MVP

A mobile-friendly **public, read-only** Streamlit app with a daily GitHub Actions collection workflow. It targets music and arts grants, poetry and writing, audio engineering, data analytics, residencies, fellowships, and competitions. Worldwide/US/remote results are allowed; eligibility is not automatically verified.

## Deploy from your phone (GitHub + Streamlit Community Cloud)

1. Create a new **public GitHub repository** (e.g. `opportunity-radar`). Upload **all files and folders**, including `.github/workflows/scan.yml` and `.streamlit/config.toml`, preserving their paths. Uploading a ZIP alone will not unpack it in GitHub.
2. Open GitHub **Actions** → **Update opportunities** → **Run workflow**. This runs the first collection and commits `radar.db`. If it fails, inspect Actions logs. Grants.gov may reject requests or return no results.
3. Visit https://share.streamlit.io/ and sign in with GitHub. Select your repository, branch `main`, and entrypoint `app.py`, then deploy.
4. Open the resulting `*.streamlit.app` URL on your phone. On iPhone use Safari Share → Add to Home Screen; on Android use Chrome menu → Add to Home screen.
5. The scheduled workflow scans daily (GitHub schedules are best-effort). Streamlit Community Cloud redeploys when the repo changes. The database is committed to GitHub, so **do not put private user data in it**.

## Sources and configuration

Edit `config.json` to add authorized HTTPS RSS feeds and specific Greenhouse, Lever, or Ashby public board slugs. Blank board slugs do nothing. Grants.gov search keywords are configured by default; verify API behavior and grant eligibility. Other arts/grant sources are **not connected automatically**. Respect source terms, rate limits, copyright, and robots directives.

## Run locally

```bash
pip install -r requirements.txt
python collector.py
streamlit run app.py
```

## Limitations and business launch requirements

- This is a **public catalog**, not a multi-user SaaS product. There are no accounts, private saved items, payment processing, or personalized email alerts.
- The original private prototype's status-editing feature was deliberately removed from the public version: SQLite on Streamlit hosting is not reliable durable multi-user storage.
- Current ranking is keyword-based; no AI eligibility decisions. No verified open/closed state or guaranteed job availability.
- Before monetizing: use a managed database, login/auth, per-user saved listings, proper privacy/terms, licensed source agreements, monitoring, moderation, and billing. Avoid collecting personal applicant information in this public GitHub database.
- Grant search may be broad or imperfect; validate links and results before marketing them as current.
