# Frontend API Environment Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Select the frontend API base URL from the Vite development or production environment.

**Architecture:** Vite loads mode-specific `.env` files at build time. The API client consumes the single `VITE_API_URL` variable directly so the deployed bundle always contains the configured endpoint.

**Tech Stack:** Vite 5, TypeScript, Vitest.

## Global Constraints

- Development URL must be exactly `http://localhost:8000`.
- Production URL must be exactly `http://8.134.48.198`.
- The API client must not silently fall back to a localhost address.

---

### Task 1: Configure API URLs by Vite mode

**Files:**
- Create: `frontend/.env.development`
- Create: `frontend/.env.production`
- Modify: `frontend/src/api.ts:1`
- Test: `frontend` production build output

**Interfaces:**
- Consumes: Vite's build-time `import.meta.env.VITE_API_URL` string.
- Produces: the exported `API_URL` constant used by all fetch calls in `frontend/src/api.ts`.

- [ ] **Step 1: Define the expected production endpoint check**

Run from `frontend` after the configuration files are added:

```powershell
npm run build
rg -n -F 'http://8.134.48.198' dist
```

Expected: before the configuration exists, the URL search finds no production endpoint in the built files.

- [ ] **Step 2: Add the mode-specific variables and consume the variable directly**

Create `frontend/.env.development`:

```dotenv
VITE_API_URL=http://localhost:8000
```

Create `frontend/.env.production`:

```dotenv
VITE_API_URL=http://8.134.48.198
```

Replace the first line of `frontend/src/api.ts` with:

```ts
export const API_URL = import.meta.env.VITE_API_URL;
```

- [ ] **Step 3: Build the production bundle and check its endpoint**

Run from `frontend`:

```powershell
npm run build
rg -n -F 'http://8.134.48.198' dist
```

Expected: `npm run build` exits with code 0, and the compiled JavaScript contains `http://8.134.48.198`.

- [ ] **Step 4: Run the existing frontend tests**

Run from `frontend`:

```powershell
npm test
```

Expected: Vitest completes with no failures.

- [ ] **Step 5: Commit the implementation**

```powershell
git add frontend/.env.development frontend/.env.production frontend/src/api.ts
git commit -m "feat: configure frontend API by environment"
```
