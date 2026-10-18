# GlobalChat

I built this as a learning project back in 9th grade (2025–2026). It’s a Flask chat + mini-game server with a tiny in-app economy (“globes”), lootboxes, leaderboards, and a deliberate “stealth mask” that makes the site look like a professional node/telemetry portal — until you open it the right way.

Quick pitch
- A simple, hands-on demo for web backend & UX ideas: sessions, DB models, transactions, rate-limiting, RNG/loot, and telemetry-driven milestones.
- Dual-mode UI: a polished docs/telemetry shell that hides a stealth chat/game app revealed by a specific breadcrumb click sequence.
- Not an active project anymore — this was a dev experiment I made while learning in 9th grade.

How the stealth mask works (plain)
1. Public face: the homepage shows a polished "SNS Reconciliation" docs UI so it looks like an enterprise docs portal.  
2. Breadcrumb vector: the docs client keeps a short trace buffer of pages you click.  
3. Secret sequence: click the right sequence of docs links and the client redirects you to an internal verification page.  
4. Verification: the server updates your session/account state when you hit that internal page.  
5. Reveal: after verification the docs client hides the documentation shell and mounts a closed Shadow DOM iframe that loads the stealth chat UI — the chat replaces the docs view.  
6. Panic switch: if an admin flips the panic toggle, the server reports integrity_check=1 and the client re-applies the mask, sending users back to the docs/health view.

Why I did it / what it shows
- Shows how UI routing, client-side state buffers, and redirects can present multiple personas for the same product.
- Good for gated demos, internal features, or easter-egg-style reveals in prototypes.
- Useful to experiment with session conversion (guest → registered), ephemeral reveals, and telemetry-driven UX.

Key endpoints used in the flow
- Docs page (mask): `/` → documentation.html  
- Verification (internal): `/api/v1/session/reconciliation-view.html`  
- Stealth chat mount: `/api/v1/session/sync/view-instance.html`  
- Telemetry/panic read: `/api/v1/system/heartbeat/state` (returns integrity_check)  
- Panic toggle (admin): `/api/v1/internal/admin/gatekeeper` (toggles panic_switch)

Run it (short)
1. Install deps:
   ```bash
   python -m pip install -r requirements.txt
   
