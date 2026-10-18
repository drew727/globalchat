# GlobalChat

I built this as a learning project back in 9th grade (2025–2026). It’s a Flask chat + mini-game server with a tiny in-app economy (“globes”), lootboxes, leaderboards, and a deliberate “stealth mask” that makes the site look like a professional node/telemetry portal — until you open it the right way.

## Quick pitch
- A simple, hands-on demo for web backend & UX ideas: sessions, DB models, transactions, rate-limiting, RNG/loot, and telemetry-driven milestones.
- Dual-mode UI: a polished docs/telemetry shell that hides a stealth chat/game app revealed by a specific breadcrumb click sequence.
- Not an active project anymore — this was a dev experiment I made while learning in 9th grade.

## How the stealth mask works (plain)
1. Public face: the homepage shows a polished "SNS Reconciliation" docs UI so it looks like an enterprise docs portal.  
2. Breadcrumb vector: the docs client keeps a short trace buffer of pages you click.  
3. Secret sequence: click the right sequence of docs links and the client redirects you to an internal verification page.  
4. Verification: the server updates your session/account state when you hit that internal page.  
5. Reveal: after verification the docs client hides the documentation shell and mounts a closed Shadow DOM iframe that loads the stealth chat UI — the chat replaces the docs view.  
6. Panic switch: if an admin flips the panic toggle, the server reports integrity_check=1 and the client re-applies the mask, sending users back to the docs/health view.

## Why I did it / what it shows
- Shows how UI routing, client-side state buffers, and redirects can present multiple personas for the same product.
- Good for gated demos, internal features, or easter-egg-style reveals in prototypes.
- Useful to experiment with session conversion (guest → registered), ephemeral reveals, and telemetry-driven UX.

## Key endpoints used in the flow
- Docs page (mask): `/` → documentation.html  
- Verification (internal): `/api/v1/session/reconciliation-view.html`  
- Stealth chat mount: `/api/v1/session/sync/view-instance.html`  
- Telemetry/panic read: `/api/v1/system/heartbeat/state` (returns integrity_check)  
- Panic toggle (admin): `/api/v1/internal/admin/gatekeeper` (toggles panic_switch)

## Run it (short)
1. Install deps:
```bash
python -m pip install -r requirements.txt
```

2. Set env (example):
```bash
export DATABASE_URL='postgresql+psycopg2://user:pass@host/db'
export SECRET_KEY='a-secret'
export FLASK_APP=main.py
```

3. DB migrations (one-time; skip if you manage schema another way):
```bash
flask db init       # only if migrations folder doesn't exist
flask db migrate
flask db upgrade
```

4. Run:
```bash
python main.py
# or for production:
gunicorn main:app
```

## Replace the demo domain with your own hosting domain
- The docs and some templates reference `systemnodesync.dpdns.org`. Before you deploy or link this repo to a real domain, replace those occurrences with your own domain so fetches, canonical links, sitemap, and CORS are correct.
- Places to check and update:
  - `templates/documentation.html` — canonical link and any meta tags; demo fetch URLs in the file.
  - `main.py` — sitemap generation: the `base_url` variable near `sitemap()` (change `"https://systemnodesync.dpdns.org"` to your domain). Also update CORS origins in the `CORS(...)` call.
  - `robots.txt` rendering in `main.py` (it references the sitemap URL).
  - `vercel.json` or any deployment config files (if present).

- Quick replace commands (run from repo root):
```bash
# preview occurrences first
git grep "systemnodesync.dpdns.org"

# replace in files (example using GNU sed; backup recommended)
sed -i 's/systemnodesync.dpdns.org/your-domain.example/g' templates/*.html main.py vercel.json
```

- After you replace the domain:
  - Update CORS allowed origins to exactly match your deployed domain.
  - Re-generate sitemap and test `/sitemap.xml` and `/robots.txt` to confirm links point to your domain.

## Safety & notes
- This repo includes dev tools (an SQL executor endpoint and a panic toggle). These are convenient for testing but dangerous if public — remove or lock them before any production deployment.
- The stealth flow depends on client-side code and session state — don’t use it to hide anything illegal or harmful. Use responsibly.
- Replace any example/fallback credentials in `main.py` and review CORS and admin access before exposing the app.
- Again: not currently active — it’s a learning/demo project from 2025–2026.
