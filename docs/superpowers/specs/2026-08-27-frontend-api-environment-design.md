# Frontend API Environment Configuration Design

## Goal

Configure the frontend API base URL through Vite environment files so that local development uses the local backend and production uses the public server endpoint.

## Configuration

- `frontend/.env.development` sets `VITE_API_URL` to `http://localhost:8000`.
- `frontend/.env.production` sets `VITE_API_URL` to `http://8.134.48.198`.
- `frontend/src/api.ts` reads `VITE_API_URL` directly and does not provide a localhost fallback. This makes a missing build-time configuration visible instead of silently sending production traffic to a local address.

## Verification

Run the frontend production build. Vite loads `.env.production` for this command, and the compiled asset should contain the production API URL rather than the localhost URL.
