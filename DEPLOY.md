# Putting LiveTrip online

LiveTrip runs as one container on [Render](https://render.com): it serves the website and the API from one HTTPS
address, which is also what lets phones install it as an app. The setup lives in `Dockerfile` and `render.yaml`.

Cost: a Starter instance plus a small disk, roughly $7-10 a month (see [Render's pricing](https://render.com/pricing)).
The free tier can't attach a disk, so every deploy would erase all trips, accounts and photos.

## Deploy

1. Sign in at [render.com](https://render.com) with the GitHub account that owns the repository.
2. Choose **New > Blueprint** and pick the repository. Render reads `render.yaml`.
3. Paste your keys when asked, using the values in `Backend/Backend/app/.env`:
   - `GOOGLE_PLACES_API_KEY`, `GEMINI_API_KEY`
   - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
4. Create it and wait for the first build (several minutes). Your site is at `https://livetrip-XXXX.onrender.com`.

`LIVETRIP_SECRET_KEY` is generated for you. Later pushes to `feature/livetrip-features` deploy automatically; to deploy
from another branch, change `branch` in `render.yaml`.

## After the first deploy

- **Google sign-in:** in Google Cloud > Credentials > your OAuth client, add this authorized redirect URI:
  `https://YOUR-ADDRESS/api/auth/google/callback`. If the consent screen is in "Testing", only the test users you
  list can sign in; publish it to open sign-in to everyone.
- **Protect your API keys:** in Google Cloud, limit each key to the API it needs, and set a budget alert on the billing
  account if you've enabled billing. The site rate-limits each visitor, but keys are still yours to watch.
- **Install it:** open the address on a phone. Android/Chrome: the Install button in the navbar. iPhone: Safari > Share >
  Add to Home Screen.

## Custom domain

Add it under the service's **Settings > Custom Domains**, set the environment variable `PUBLIC_APP_URL` to
`https://your-domain`, and add the matching Google redirect URI.

## Good to know

- **Data:** everything lives on the disk at `/data` in one SQLite database plus the uploaded photos. Render snapshots
  disks daily, which is what you'd restore from. This suits one server; growing beyond that means moving to Postgres.
- **Your local data stays local:** the production site starts empty apart from the sample destinations.
- **Older features are off in production:** SOS/SMS, flights, notifications, location tracking and the API docs.
  They have no sign-in checks and the website doesn't use them. See `_keep` in `livetrip/production.py`.
- **Try production mode locally** (needs `npm run build` in `frontend/` first), from `Backend/Backend/app`:
  set `LIVETRIP_ENV=production` and `LIVETRIP_SECRET_KEY=anything`, then run `python -m uvicorn main:app --port 8000`.
