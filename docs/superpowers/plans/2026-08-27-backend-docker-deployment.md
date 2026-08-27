# Backend Docker Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the FastAPI backend as a deployable Docker image and make the existing Compose deployment persist role data on the server.

**Architecture:** Build the backend image locally from `backend/` with Python 3.12 slim, then export and import it on the server as `resume-backend:local`. Compose starts that local image, injects runtime environment values, and bind-mounts the server's `data/` directory to `/data`, selected by `ROLES_FILE`.

**Tech Stack:** Docker, Docker Compose, Python 3.12, FastAPI, Uvicorn.

## Global Constraints

- `docker save` runs locally; `docker load` and Compose run in `/opt/resumeRecognition/backend` on the server.
- The API uses exactly one Uvicorn worker because batch state is held in process memory.
- `.env.production` must not be included in the image.
- `data/roles.json` persists through the host `./data` directory.

---

### Task 1: Add a production container definition

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`

**Interfaces:**
- Consumes: `backend/requirements.txt`, `backend/app/main.py`
- Produces: a Docker image listening on TCP port `8000` and running `app.main:app` with one worker.

- [ ] **Step 1: Verify the build is currently unavailable**

Run: `docker build -t resume-backend:local ./backend`

Expected: FAIL because `backend/Dockerfile` does not exist.

- [ ] **Step 2: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

- [ ] **Step 3: Create `backend/.dockerignore`**

```text
.env
.env.*
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
tests/
data/
```

- [ ] **Step 4: Build the image**

Run: `docker build -t resume-backend:local ./backend`

Expected: PASS and report a successfully tagged `resume-backend:local` image.

- [ ] **Step 5: Commit the container definition**

```bash
git add backend/Dockerfile backend/.dockerignore
git commit -m "build: add backend docker image"
```

### Task 2: Make Compose build and persist production data

**Files:**
- Modify: `backend/compose.yml`

**Interfaces:**
- Consumes: `backend/Dockerfile`, `backend/.env.production`, host directory `backend/data/`
- Produces: `docker compose up -d --no-build --pull never` deployment exposing port `8000` and storing roles in `/data/roles.json`.

- [ ] **Step 1: Verify the current Compose configuration does not select the mounted data path**

Run: `docker compose -f backend/compose.yml config`

Expected: PASS, but the rendered `backend` environment does not contain `ROLES_FILE=/data/roles.json` and it references the wrong image tag.

- [ ] **Step 2: Replace the `backend` service in `backend/compose.yml`**

```yaml
services:
  backend:
    image: resume-backend:local
    container_name: resume-backend
    restart: unless-stopped
    env_file:
      - ./.env.production
    environment:
      ROLES_FILE: /data/roles.json
    volumes:
      - ./data:/data
    ports:
      - "8000:8000"
```

- [ ] **Step 3: Validate the rendered Compose configuration**

Run: `docker compose -f backend/compose.yml config`

Expected: PASS; output includes `image: resume-backend:local`, `ROLES_FILE: /data/roles.json`, `./data:/data`, `8000:8000`, and `.env.production` is only an `env_file`.

- [ ] **Step 4: Build and start the server deployment**

Run from `/opt/resumeRecognition/backend`: `docker compose up -d --no-build --pull never`

Expected: PASS; the `resume-backend` container is running and has one Uvicorn worker.

- [ ] **Step 5: Verify the health endpoint**

Run: `curl --fail http://127.0.0.1:8000/health`

Expected: PASS with `{"status":"ok"}`.

- [ ] **Step 6: Commit the Compose deployment configuration**

```bash
git add backend/compose.yml
git commit -m "build: configure backend compose deployment"
```
