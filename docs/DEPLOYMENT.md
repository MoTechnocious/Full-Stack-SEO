# MySEOapp — Local Run & Deployment Guide

Monorepo: `backend` (FastAPI, Python), `frontend` (Next.js 14, TS), `mcp-server` (TypeScript, stdio MCP).

---

## Part 1 — Run locally to test

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### 1. Backend (FastAPI)

```bash
cd MySEOapp/backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp ../.env.template ../.env
# edit ../.env — for local testing the defaults work as-is (SQLite, mock providers)

python -m pytest -q                # 89 tests should pass
uvicorn app.main:app --reload --port 8000
```

Verify: open `http://localhost:8000/docs` (OpenAPI/Swagger UI).

### 2. Frontend (Next.js)

In a second terminal:

```bash
cd MySEOapp/frontend
npm install
# ensure ../.env (or frontend/.env.local) has:
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run typecheck
npm run dev
```

Verify: open `http://localhost:3000`. If the backend isn't running, pages fall back to mock data — that's expected behavior, not a bug.

### 3. MCP server (TypeScript)

In a third terminal:

```bash
cd MySEOapp/mcp-server
rm -rf node_modules      # avoids stale-lock issues, especially on cloud-synced folders
npm install
npm run build
npm test
node dist/index.js
```

To use it from Claude Desktop, add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "myseoapp": {
      "command": "node",
      "args": ["/absolute/path/to/MySEOapp/mcp-server/dist/index.js"],
      "env": { "MYSEOAPP_API_BASE_URL": "http://localhost:8000" }
    }
  }
}
```

At this point you have all three pieces running locally and can click through the dashboard, hit the API docs, and call MCP tools.

---

## Part 2 — Deploy to a Namecheap VPS (Quasar plan)

This assumes a fresh Ubuntu VPS (22.04/24.04) from Namecheap, reachable via SSH, with a domain pointed at it (A record in Namecheap DNS → VPS IP).

### 1. Server setup

```bash
ssh root@YOUR_VPS_IP

apt update && apt upgrade -y
apt install -y python3.11 python3.11-venv python3-pip nginx git curl ufw

# Node 18 LTS via nodesource
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs

npm install -g pm2

# Firewall: only allow SSH, HTTP, HTTPS
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
```

Create a non-root deploy user (recommended over running as root):

```bash
adduser deploy
usermod -aG sudo deploy
su - deploy
```

### 2. Get the code onto the server

```bash
git clone <your-repo-url> ~/MySEOapp
cd ~/MySEOapp
```

(Or `scp -r` the folder up if it's not in git yet.)

### 3. Backend — production config and service

```bash
cd ~/MySEOapp/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

cp ../.env.template ../.env
```

Edit `~/MySEOapp/.env` for production — at minimum change these from their defaults:

| Variable | Set to |
|---|---|
| `SEO_ENVIRONMENT` | `production` |
| `SEO_DEBUG` | `false` |
| `SEO_CORS_ALLOW_ORIGINS` | `["https://app.yourdomain.com"]` (your real frontend origin, not `*`) |
| `SEO_DATABASE_URL` | Postgres, e.g. `postgresql+psycopg2://user:pass@localhost:5432/myseoapp` (SQLite is fine for a low-traffic single-VPS setup, but Postgres is safer given the multi-tenant/billing tables) |
| `SEO_JWT_SECRET` | a long random string (`openssl rand -hex 32`) |
| `SEO_WEBHOOK_SIGNING_SECRET` | a long random string |
| `SEO_IDP_PROVIDER` | `dev` to start, or `clerk`/`supabase`/`auth0` if you're wiring real auth |
| `SEO_MAKE_WEBHOOK_URL` / `SEO_MAKE_SIGNING_SECRET` | your Make.com scenario webhook + shared secret, once ready |

If using Postgres, install it and create the DB:

```bash
sudo apt install -y postgresql
sudo -u postgres createuser myseoapp -P
sudo -u postgres createdb myseoapp -O myseoapp
```

Run the test suite once against the real config before going live:

```bash
python -m pytest -q
```

Run the API with Gunicorn + Uvicorn workers under systemd (don't use `--reload` in production):

```bash
sudo tee /etc/systemd/system/myseoapp-backend.service > /dev/null <<'EOF'
[Unit]
Description=MySEOapp FastAPI backend
After=network.target

[Service]
User=deploy
WorkingDirectory=/home/deploy/MySEOapp/backend
EnvironmentFile=/home/deploy/MySEOapp/.env
ExecStart=/home/deploy/MySEOapp/backend/.venv/bin/gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker --workers 3 --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now myseoapp-backend
sudo systemctl status myseoapp-backend
```

### 4. Frontend — build and run

```bash
cd ~/MySEOapp/frontend
npm install
# set in ~/MySEOapp/.env or frontend/.env.production:
# NEXT_PUBLIC_API_BASE_URL=https://api.yourdomain.com
npm run build
pm2 start npm --name myseoapp-frontend -- start -- -p 3000
pm2 save
pm2 startup   # follow the printed command to enable pm2 on boot
```

### 5. Nginx reverse proxy + SSL

```bash
sudo tee /etc/nginx/sites-available/myseoapp > /dev/null <<'EOF'
server {
    listen 80;
    server_name app.yourdomain.com;
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name api.yourdomain.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/myseoapp /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d app.yourdomain.com -d api.yourdomain.com
```

Certbot will auto-renew via a systemd timer it installs.

### 6. DNS (Namecheap)

In Namecheap's DNS management for your domain, add:
- `A` record: `app` → your VPS IP
- `A` record: `api` → your VPS IP

### 7. MCP server on the VPS (optional)

The MCP server talks over stdio, so it isn't "hosted" like a web service — it runs on whatever machine has the MCP client (e.g. your own laptop's Claude Desktop), pointed at the production API:

```json
{
  "mcpServers": {
    "myseoapp": {
      "command": "node",
      "args": ["/absolute/path/to/MySEOapp/mcp-server/dist/index.js"],
      "env": {
        "MYSEOAPP_API_BASE_URL": "https://api.yourdomain.com",
        "MYSEOAPP_API_KEY": "<a real API key issued by the backend>"
      }
    }
  }
}
```

Build it locally (`npm run build`) — no need to run it on the VPS unless you specifically want a shared server-side instance.

### 8. Verify

- `https://app.yourdomain.com` loads the dashboard
- `https://api.yourdomain.com/docs` loads Swagger
- `sudo journalctl -u myseoapp-backend -f` and `pm2 logs myseoapp-frontend` for live logs

---

## Part 3 — Deploy to Vercel

Vercel is a strong fit for the **frontend** (Next.js is a first-class citizen there). It's a poor fit for this **backend**: the FastAPI app holds in-memory state (rate limiter, request-scoped store) and Vercel's serverless functions are stateless and cold-start per invocation, so rate limiting and any in-memory data would silently reset. Recommended split: frontend on Vercel, backend kept on a real host (the Namecheap VPS above, or Render/Railway/Fly.io if you want a managed alternative).

### 1. Frontend on Vercel

```bash
npm install -g vercel
cd MySEOapp/frontend
vercel login
vercel link
```

In the Vercel dashboard (or via `vercel env add`), set:
- `NEXT_PUBLIC_API_BASE_URL` = `https://api.yourdomain.com` (your VPS-hosted backend, or wherever it lives)

Deploy:

```bash
vercel --prod
```

Vercel auto-detects Next.js, runs `npm run build`, and serves it on a `*.vercel.app` URL (or your custom domain if you attach one under Project Settings → Domains).

### 2. Backend — if you still want it on Vercel anyway

Technically possible via Vercel's Python runtime (`vercel.json` with a `@vercel/python` build, restructuring `app/main.py` as a serverless handler), but you'd lose:
- The in-memory rate limiter (resets every cold start)
- Simple background/long-running crawl jobs (serverless functions have execution time limits)
- The always-on `uvicorn` process model the app is built around

If low ops overhead matters more than staying off Vercel, Render or Railway give you a persistent container (closer to the VPS model) with a simpler push-to-deploy flow than raw Vercel serverless — worth considering as a third option alongside the VPS.

### 3. Verify

- Vercel deployment URL loads the dashboard
- Confirm `NEXT_PUBLIC_API_BASE_URL` requests succeed (browser devtools → Network tab) against the real backend, not mock data

---

## Database migrations (Alembic)

Schema changes are managed with Alembic (`backend/alembic.ini` + `backend/alembic/`).
The migration environment reads the database URL from the app settings — set
`SEO_DATABASE_URL` (or rely on the SQLite dev default) and run every command from
`backend/`. `init_db()` / `SQLModel.metadata.create_all()` remains a dev/test
convenience only; production schemas are created and evolved exclusively via Alembic.

### Apply migrations (deploy step)

```bash
cd backend
alembic upgrade head          # bring the DB to the latest revision
alembic current               # verify which revision is applied
```

Run `alembic upgrade head` on every deploy **before** starting/reloading the API
process. On a brand-new database this creates the full schema (revision
`0001_initial_schema`).

### Create a new revision after changing models

```bash
cd backend
# 1. Edit app/db/models_*.py (new table/column/index)
# 2. Autogenerate a candidate migration against an up-to-date DB:
alembic revision --autogenerate -m "add_widget_leads_table"
# 3. REVIEW the generated file in alembic/versions/ (autogenerate misses
#    server defaults, data backfills, and some type changes), then:
alembic upgrade head
```

To target a specific database without touching `.env`, pass it explicitly:

```bash
alembic -x db_url=postgresql+psycopg://user:pass@host:5432/myseoapp upgrade head
```

### Roll back

```bash
alembic downgrade -1          # revert the most recent revision
alembic downgrade base        # drop everything managed by migrations
alembic history --verbose     # inspect the revision chain
```

Offline mode (generate SQL for a DBA instead of applying directly) is supported:
`alembic upgrade head --sql > migrate.sql`.

`backend/tests/test_migrations.py` keeps migrations honest: it asserts that
`upgrade head` on a fresh database matches `SQLModel.metadata` table-for-table and
column-for-column, and that `downgrade base` is clean.

---

## Production checklist (either target)

- [ ] `SEO_CORS_ALLOW_ORIGINS` restricted to real frontend origin(s), not `["*"]`
- [ ] `SEO_JWT_SECRET` and `SEO_WEBHOOK_SIGNING_SECRET` rotated from template defaults
- [ ] `SEO_DATABASE_URL` pointed at Postgres (not the SQLite dev default) if you expect concurrent users
- [ ] `alembic upgrade head` run against the production DB (see "Database migrations")
- [ ] `.env` is not committed to git (check `.gitignore`)
- [ ] Backend test suite green against production-like config: `python -m pytest -q`
- [ ] MCP server test suite green: `npm test` (in `mcp-server/`)
- [ ] HTTPS working on both frontend and API domains
- [ ] Logs are structured JSON (`SEO_LOG_JSON=true`) and reachable (`journalctl` / pm2 logs / your log aggregator)
