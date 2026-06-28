# BUILD 14 — Cloud Deployment

> **Status (2026-05-20):** This generic single-VM Docker-compose spec is
> superseded by [Railway-Deployment-Plan.md](../Railway-Deployment-Plan.md)
> as the **primary production target**. Railway gives us managed Redis,
> always-on container, and a 10 GB volume in one PaaS project — the
> single-VM topology below is kept for reference as a self-hosted
> alternative. The [Render-Migration-Plan.md](../Render-Migration-Plan.md)
> covers a second PaaS alternative (two-service split, similar cost).

> **Goal:** Stand up a production-grade Enigmatrix deployment on a single 4-vCPU / 16 GB cloud VM running Docker and docker-compose, fronted by nginx with TLS, with automated backups, blue/green releases, GitHub Actions CI/CD, and a written disaster recovery runbook.
>
> **Read first:** BUILD_03 (Backend API), BUILD_04 (Database and Storage), BUILD_15 (Observability and Testing).

> **Scope:** A single-VM dockerized topology that runs every Enigmatrix service (FastAPI backend, Next.js frontend, PostgreSQL 16, ChromaDB, Redis, Celery worker + beat, Label Studio) behind one nginx instance with Let's Encrypt TLS. Covers secret layering, nightly backups to S3-compatible object storage, blue/green deployment via two compose projects, a GitHub Actions pipeline that builds images, pushes to GHCR, and ssh-deploys, plus a DR runbook with concrete RTO and RPO targets. Multi-region failover, Kubernetes, service mesh, and managed cloud databases are explicitly out of scope; if the deployment ever needs them, fork this file rather than expanding it.

---

## 1. Topology

The whole stack lives on one VM. Services talk over a private docker network; only nginx publishes ports 80 and 443 to the host. Postgres, Chroma, Redis, and Label Studio never expose themselves to the public internet.

```
                          Internet (443/80)
                                 |
                                 v
+--------------------------------------------------------------+
|  VM: 4 vCPU / 16 GB RAM / 80 GB SSD / Ubuntu 22.04 LTS        |
|                                                              |
|   +-------------------+                                      |
|   |  nginx (TLS)      |  certbot renewal cron                |
|   |  256 MB           |                                      |
|   +---------+---------+                                      |
|             | upstream                                       |
|     +-------+--------+----------------+                      |
|     v                v                v                      |
|  backend          frontend       label-studio                |
|  FastAPI          Next.js        :8080 (admin only)          |
|  gunicorn         standalone                                 |
|  uvicorn workers  node:20-alpine                             |
|  :8000            :3000                                      |
|     |                                                        |
|     +---> postgres:5432   (volume: pgdata)                   |
|     +---> chromadb:8000-internal (volume: chromadata)        |
|     +---> redis:6379                                         |
|                                                              |
|  celery-worker  <--- redis broker --->  celery-beat          |
|  (ml image,                                                  |
|   torch+hf)                                                  |
|                                                              |
|  backup cron: pg_dump.sh + chroma_snapshot.sh -> S3          |
+--------------------------------------------------------------+
```

The compose project name is parameterised so the same file can run as `enigmatrix_blue` or `enigmatrix_green` side-by-side during a release.

---

## 2. Resource Budget

The VM is small. Every service has an explicit memory ceiling enforced by docker-compose so that a single misbehaving worker cannot OOM the host. CPU shares are advisory; memory limits are hard.

| Service        | vCPU (shares) | RAM limit | Notes                                                |
|----------------|---------------|-----------|------------------------------------------------------|
| nginx          | 0.25          | 256 MB    | Static reverse proxy, gzip, TLS.                     |
| backend        | 1.0           | 2.0 GB    | gunicorn 2 uvicorn workers, lean image (no torch).   |
| frontend       | 0.5           | 1.0 GB    | Next.js standalone server, prebuilt.                 |
| postgres       | 1.0           | 4.0 GB    | shared_buffers=1GB, effective_cache_size=2GB.        |
| chromadb       | 0.5           | 2.0 GB    | Persistence on local volume.                         |
| redis          | 0.25          | 512 MB    | maxmemory 384 MB, allkeys-lru.                       |
| celery-worker  | 1.0           | 2.0 GB    | Heavier ML image, concurrency=2.                     |
| celery-beat    | 0.1           | 256 MB    | Scheduler only.                                      |
| label-studio   | 0.4           | 1.0 GB    | Gated behind nginx basic-auth on /annotate.          |
| OS + buffers   | -             | 2.0 GB    | systemd, journald, page cache headroom.              |
| **Total**      | **~5.0**      | **15.0 GB** | Fits in 16 GB with ~1 GB safety margin.            |

CPU oversubscription (5.0 against 4 vCPU) is intentional: postgres, celery, and the backend rarely peak simultaneously. If they do, postgres wins via a higher `cpu_shares`.

---

## 3. Dockerfiles

Three images. The API image stays lean (no torch, no transformers) so that it pulls and starts fast. The ML image carries the heavy dependencies and runs only as the Celery worker. The frontend uses Next.js standalone output for a small runtime image.

The canonical resolved lock files are committed in the repo: `apps/backend/uv.lock` and `apps/frontend/pnpm-lock.yaml`. The Dockerfiles must invoke the package managers in their frozen / `--frozen-lockfile` modes so that builds are byte-reproducible from those lockfiles. If a build needs a dependency that is not in the lockfile, the lockfile is updated in a separate PR — never inside the Dockerfile.

### 3.1 `apps/backend/Dockerfile`

```dockerfile
# syntax=docker/dockerfile:1.7

# ---------- builder ----------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.4.30

WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

# ---------- runtime ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl tini \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash --uid 10001 app

WORKDIR /app
COPY --from=builder --chown=app:app /build /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["gunicorn", "enigmatrix.main:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "60", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-"]
```

Two workers is deliberate: with 4 vCPU the rule of thumb is `(2 * cores) + 1`, but Celery and postgres also need cores. Two uvicorn workers handle the API load comfortably given that ML calls are offloaded.

### 3.2 `apps/frontend/Dockerfile` (sketch)

```dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN corepack enable && pnpm build  # produces .next/standalone

FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production PORT=3000
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s CMD wget -qO- http://127.0.0.1:3000/api/health || exit 1
CMD ["node", "server.js"]
```

### 3.3 `apps/ml/Dockerfile.worker` (sketch)

```dockerfile
FROM python:3.11-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.4.30
WORKDIR /app
COPY apps/ml/pyproject.toml apps/ml/uv.lock ./
RUN uv sync --frozen --no-dev      # includes torch, transformers, sentence-transformers
COPY apps/ml ./
USER 10001
CMD ["celery", "-A", "enigmatrix_ml.celery_app", "worker", \
     "--loglevel=INFO", "--concurrency=2", "--max-tasks-per-child=50"]
```

`--max-tasks-per-child=50` recycles worker processes to free memory leaked by long-running model calls.

---

## 4. `docker-compose.yml`

This is the production base file. It is checked in. Secrets come from `.env` (never committed) and per-service `env_file` references. Volumes are named so that they survive `docker compose down`. Healthchecks are mandatory — the deploy script blocks on them.

```yaml
name: enigmatrix
x-restart: &restart
  restart: unless-stopped

services:
  nginx:
    image: nginx:1.27-alpine
    <<: *restart
    ports: ["80:80", "443:443"]
    volumes:
      - ./infra/nginx/enigmatrix.conf:/etc/nginx/conf.d/default.conf:ro
      - letsencrypt:/etc/letsencrypt:ro
      - certbot-www:/var/www/certbot:ro
    depends_on:
      backend: { condition: service_healthy }
      frontend: { condition: service_healthy }
    deploy:
      resources: { limits: { cpus: "0.25", memory: 256M } }

  backend:
    image: ghcr.io/enigmatrix/backend:${IMAGE_TAG:-latest}
    <<: *restart
    env_file: [.env, .env.backend]
    depends_on:
      postgres: { condition: service_healthy }
      redis:    { condition: service_healthy }
      chromadb: { condition: service_started }
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://127.0.0.1:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s
    deploy:
      resources: { limits: { cpus: "1.0", memory: 2G } }

  frontend:
    image: ghcr.io/enigmatrix/frontend:${IMAGE_TAG:-latest}
    <<: *restart
    env_file: [.env, .env.frontend]
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://127.0.0.1:3000/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    deploy:
      resources: { limits: { cpus: "0.5", memory: 1G } }

  celery-worker:
    image: ghcr.io/enigmatrix/ml-worker:${IMAGE_TAG:-latest}
    <<: *restart
    env_file: [.env, .env.backend]
    depends_on:
      redis: { condition: service_healthy }
      postgres: { condition: service_healthy }
    deploy:
      resources: { limits: { cpus: "1.0", memory: 2G } }

  celery-beat:
    image: ghcr.io/enigmatrix/ml-worker:${IMAGE_TAG:-latest}
    command: ["celery", "-A", "enigmatrix_ml.celery_app", "beat", "--loglevel=INFO"]
    <<: *restart
    env_file: [.env, .env.backend]
    depends_on:
      redis: { condition: service_healthy }
    deploy:
      resources: { limits: { cpus: "0.1", memory: 256M } }

  postgres:
    image: postgres:16-alpine
    <<: *restart
    environment:
      POSTGRES_DB: enigmatrix
      POSTGRES_USER: enigmatrix
      POSTGRES_PASSWORD_FILE: /run/secrets/pg_password
    volumes:
      - pgdata:/var/lib/postgresql/data
    secrets: [pg_password]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U enigmatrix -d enigmatrix"]
      interval: 10s
      timeout: 5s
      retries: 5
    command: >
      postgres
      -c shared_buffers=1GB
      -c effective_cache_size=2GB
      -c work_mem=16MB
      -c max_connections=100
    deploy:
      resources: { limits: { cpus: "1.0", memory: 4G } }

  chromadb:
    image: chromadb/chroma:0.5.20
    <<: *restart
    volumes:
      - chromadata:/chroma/chroma
    environment:
      IS_PERSISTENT: "TRUE"
      ANONYMIZED_TELEMETRY: "FALSE"
    deploy:
      resources: { limits: { cpus: "0.5", memory: 2G } }

  redis:
    image: redis:7-alpine
    <<: *restart
    command: ["redis-server", "--maxmemory", "384mb", "--maxmemory-policy", "allkeys-lru", "--appendonly", "yes"]
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    deploy:
      resources: { limits: { cpus: "0.25", memory: 512M } }

  label-studio:
    image: heartexlabs/label-studio:1.13.1
    <<: *restart
    env_file: [.env.labelstudio]
    volumes:
      - lsdata:/label-studio/data
    deploy:
      resources: { limits: { cpus: "0.4", memory: 1G } }

volumes:
  pgdata:
  chromadata:
  redisdata:
  lsdata:
  letsencrypt:
  certbot-www:

secrets:
  pg_password:
    file: ./infra/secrets/pg_password.txt
```

### 4.1 `docker-compose.override.yml`

The override file is environment-specific and is selected by symlink (`docker-compose.override.yml -> docker-compose.staging.yml` or `docker-compose.production.yml`). It changes nothing about images — only environment, log level, and exposed ports.

```yaml
# docker-compose.production.yml (symlinked as override on the prod VM)
services:
  backend:
    environment:
      ENV: production
      LOG_LEVEL: INFO
      SENTRY_TRACES_SAMPLE_RATE: "0.05"
  frontend:
    environment:
      NEXT_PUBLIC_ENV: production
  postgres:
    command: >
      postgres
      -c shared_buffers=1GB
      -c effective_cache_size=2GB
      -c log_min_duration_statement=500
```

```yaml
# docker-compose.staging.yml
services:
  backend:
    environment:
      ENV: staging
      LOG_LEVEL: DEBUG
      SENTRY_TRACES_SAMPLE_RATE: "1.0"
  postgres:
    command: ["postgres", "-c", "log_statement=all"]
```

---

## 5. nginx and TLS

`infra/nginx/enigmatrix.conf` is the only nginx file. It terminates TLS, redirects HTTP to HTTPS, sets HSTS, and applies a stricter rate-limit zone to authentication endpoints.

```nginx
limit_req_zone $binary_remote_addr zone=auth_zone:10m rate=5r/s;
limit_req_zone $binary_remote_addr zone=api_zone:10m  rate=30r/s;

upstream backend_upstream  { server backend:8000;  keepalive 32; }
upstream frontend_upstream { server frontend:3000; keepalive 32; }

server {
    listen 80;
    server_name enigmatrix.app www.enigmatrix.app;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl http2;
    server_name enigmatrix.app www.enigmatrix.app;

    ssl_certificate     /etc/letsencrypt/live/enigmatrix.app/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/enigmatrix.app/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;

    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    client_max_body_size 25m;

    location /api/v1/auth/ {
        limit_req zone=auth_zone burst=10 nodelay;
        proxy_pass http://backend_upstream;
        include /etc/nginx/conf.d/proxy_common.conf;
    }

    location /api/ {
        limit_req zone=api_zone burst=60 nodelay;
        proxy_pass http://backend_upstream;
        include /etc/nginx/conf.d/proxy_common.conf;
    }

    location /annotate/ {
        auth_basic "Annotators only";
        auth_basic_user_file /etc/nginx/htpasswd;
        proxy_pass http://label-studio:8080/;
        include /etc/nginx/conf.d/proxy_common.conf;
    }

    location / {
        proxy_pass http://frontend_upstream;
        include /etc/nginx/conf.d/proxy_common.conf;
    }
}
```

The initial certificate is obtained with certbot in `--standalone` mode while nginx is stopped, then renewed in webroot mode via cron:

```bash
# infra/cron/certbot.cron  (run as root, 03:17 daily)
17 3 * * * certbot renew --webroot -w /var/www/certbot --quiet \
    && docker exec enigmatrix-nginx nginx -s reload
```

---

## 6. Secrets and Environment

Secrets are layered, never inlined into images. The repo carries `.env.example` with every required name documented and a placeholder value. The real `.env` lives only on the VM (mode 0600, owned by the deploy user) and is decrypted from sops or pulled from Doppler at boot.

Required secret names:

| Name                       | Used by                | Notes                                  |
|----------------------------|------------------------|----------------------------------------|
| `DATABASE_URL`             | backend, celery        | `postgresql+asyncpg://...`             |
| `JWT_SECRET`               | backend                | 32+ random bytes, base64.              |
| `APP_SECRET_KEY`           | backend                | Cookie / session signing.              |
| `HUGGINGFACE_TOKEN`        | celery-worker          | Model downloads.                       |
| `SENTRY_DSN`               | backend, frontend      | Error reporting.                       |
| `S3_ENDPOINT_URL`          | backup scripts         | e.g. Backblaze B2 / Cloudflare R2.     |
| `S3_BUCKET`                | backup scripts         | Single bucket, prefixed paths.         |
| `S3_ACCESS_KEY_ID`         | backup scripts         | -                                      |
| `S3_SECRET_ACCESS_KEY`     | backup scripts         | -                                      |
| `REDIS_URL`                | backend, celery        | `redis://redis:6379/0`                 |
| `CHROMA_HOST`              | backend, celery        | `chromadb` service DNS.                |
| `LABEL_STUDIO_API_KEY`     | backend                | Annotation sync.                       |

Lockfile reminder: `apps/backend/uv.lock` and `apps/frontend/pnpm-lock.yaml` are the canonical resolved dependency sets and are committed. Production builds must use them in frozen mode. Never regenerate lockfiles inside CI without a corresponding repo commit.

`.env` decryption flow (sops + age):

```bash
# infra/secrets/decrypt.sh
#!/usr/bin/env bash
set -euo pipefail
export SOPS_AGE_KEY_FILE=/etc/enigmatrix/age.key
sops -d infra/secrets/env.production.enc > /opt/enigmatrix/current/.env
chmod 600 /opt/enigmatrix/current/.env
```

---

## 7. Backups

Two scripts run from the host crontab (not from inside containers, so a container crash never silently breaks backups). Both write to a local staging directory first, then sync to S3-compatible storage. Local retention is 14 days; S3 retention is governed by a bucket lifecycle rule (90 days hot, then deep archive).

### 7.1 `infra/backup/pg_dump.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DEST=/var/backups/enigmatrix/pg
mkdir -p "$DEST"

docker exec -i enigmatrix-postgres-1 \
    pg_dump -U enigmatrix -d enigmatrix --format=custom --compress=9 \
    > "$DEST/enigmatrix-$STAMP.dump"

# integrity check
test -s "$DEST/enigmatrix-$STAMP.dump"

# 14-day local retention
find "$DEST" -name 'enigmatrix-*.dump' -mtime +14 -delete

# weekly mirror to S3 (Sundays)
if [ "$(date -u +%u)" = "7" ]; then
    aws --endpoint-url "$S3_ENDPOINT_URL" s3 cp \
        "$DEST/enigmatrix-$STAMP.dump" \
        "s3://$S3_BUCKET/pg/enigmatrix-$STAMP.dump"
fi
```

Crontab entry: `30 2 * * * /opt/enigmatrix/current/infra/backup/pg_dump.sh >> /var/log/enigmatrix-backup.log 2>&1`.

### 7.2 `infra/backup/chroma_snapshot.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
SRC=/var/lib/docker/volumes/enigmatrix_chromadata/_data
DEST=/var/backups/enigmatrix/chroma
mkdir -p "$DEST"

tar -C "$SRC" -czf "$DEST/chroma-$STAMP.tar.gz" .
test -s "$DEST/chroma-$STAMP.tar.gz"
find "$DEST" -name 'chroma-*.tar.gz' -mtime +14 -delete

aws --endpoint-url "$S3_ENDPOINT_URL" s3 cp \
    "$DEST/chroma-$STAMP.tar.gz" \
    "s3://$S3_BUCKET/chroma/chroma-$STAMP.tar.gz"
```

Cron: `45 2 * * * /opt/enigmatrix/current/infra/backup/chroma_snapshot.sh >> /var/log/enigmatrix-backup.log 2>&1`.

### 7.3 Restore (summary; full runbook in §10)

```bash
# Postgres
docker compose stop backend celery-worker celery-beat
docker exec -i enigmatrix-postgres-1 \
    pg_restore -U enigmatrix -d enigmatrix --clean --if-exists \
    < /var/backups/enigmatrix/pg/enigmatrix-<STAMP>.dump
docker compose start backend celery-worker celery-beat

# Chroma
docker compose stop chromadb
sudo tar -C /var/lib/docker/volumes/enigmatrix_chromadata/_data \
    -xzf /var/backups/enigmatrix/chroma/chroma-<STAMP>.tar.gz
docker compose start chromadb
```

---

## 8. Blue/Green Deploys

Two compose projects share the host but use distinct project names, networks, and volume prefixes, except for the database and chroma volumes which are bind-mounted into both at read level only when required for migration. In normal operation only one project owns the DB volume; the other points at the same DSN once promoted.

```
+----------------+        +----------------+
| enigmatrix_blue|        |enigmatrix_green|
|  backend :8001 |        |  backend :8002 |
|  frontend:3001 |        |  frontend:3002 |
+----------------+        +----------------+
        ^                          ^
        |                          |
        +----------+   +-----------+
                   |   |
              nginx upstream switch (active.conf)
```

The active colour is recorded in `/etc/enigmatrix/active` (`blue` or `green`) and templated into nginx upstream files. Promotion script:

```bash
# infra/deploy/promote.sh
#!/usr/bin/env bash
set -euo pipefail

NEW=${1:?usage: promote.sh blue|green}
[[ "$NEW" =~ ^(blue|green)$ ]] || { echo "bad colour"; exit 2; }

# 1. health-check the candidate
PORT=$([ "$NEW" = "blue" ] && echo 8001 || echo 8002)
for i in {1..30}; do
    curl -fsS "http://127.0.0.1:$PORT/health" && break
    sleep 2
done

# 2. swap nginx upstream
sed "s/__ACTIVE__/$NEW/" /etc/enigmatrix/active.conf.tmpl \
    > /etc/nginx/conf.d/active.conf
docker exec enigmatrix-nginx nginx -t
docker exec enigmatrix-nginx nginx -s reload

# 3. mark active and drain old
echo "$NEW" > /etc/enigmatrix/active
OLD=$([ "$NEW" = "blue" ] && echo green || echo blue)
sleep 30   # drain in-flight requests
docker compose -p "enigmatrix_$OLD" stop backend frontend celery-worker
echo "promoted $NEW; previous $OLD stopped"
```

Total promotion time, including drain, is well under two minutes.

---

## 9. CI/CD

GitHub Actions builds both images, pushes them to GHCR with the commit SHA as a tag, and ssh-deploys to the VM. SSH uses an OIDC-issued short-lived key vended by a small jump service; falling back to a GitHub Actions secret SSH key is acceptable for the first iteration.

```yaml
# .github/workflows/deploy.yml
name: deploy
on:
  push:
    branches: [main]

permissions:
  contents: read
  packages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build & push backend
        uses: docker/build-push-action@v5
        with:
          context: apps/backend
          push: true
          tags: |
            ghcr.io/enigmatrix/backend:${{ github.sha }}
            ghcr.io/enigmatrix/backend:latest
          cache-from: type=gha
          cache-to:   type=gha,mode=max

      - name: Build & push frontend
        uses: docker/build-push-action@v5
        with:
          context: apps/frontend
          push: true
          tags: |
            ghcr.io/enigmatrix/frontend:${{ github.sha }}
            ghcr.io/enigmatrix/frontend:latest

      - name: Build & push ml-worker
        uses: docker/build-push-action@v5
        with:
          context: .
          file: apps/ml/Dockerfile.worker
          push: true
          tags: |
            ghcr.io/enigmatrix/ml-worker:${{ github.sha }}
            ghcr.io/enigmatrix/ml-worker:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: webfactory/ssh-agent@v0.9.0
        with:
          ssh-private-key: ${{ secrets.DEPLOY_SSH_KEY }}

      - name: Deploy candidate colour
        env:
          SHA: ${{ github.sha }}
        run: |
          ssh -o StrictHostKeyChecking=accept-new deploy@vm.enigmatrix.app bash -se <<EOF
            set -euo pipefail
            ACTIVE=\$(cat /etc/enigmatrix/active)
            CAND=\$([ "\$ACTIVE" = "blue" ] && echo green || echo blue)
            cd /opt/enigmatrix/current
            export IMAGE_TAG=$SHA
            docker compose -p enigmatrix_\$CAND pull
            docker compose -p enigmatrix_\$CAND up -d --remove-orphans
            ./infra/deploy/promote.sh \$CAND
          EOF
```

The workflow is gated on the `production` environment, which carries a manual approval rule for the deploy job.

---

## 10. Disaster Recovery Runbook

Targets: **RTO 30 minutes**, **RPO 24 hours**. The RPO is bounded by the daily pg_dump cadence.

### 10.1 VM total loss

1. Provision a fresh 4-vCPU / 16 GB Ubuntu 22.04 VM. (~5 min)
2. Run the bootstrap script (`infra/deploy/bootstrap.sh`): installs Docker, AWS CLI, sops, certbot, creates the `deploy` user, mounts the data disk. (~7 min)
3. Pull the latest pg_dump and chroma snapshot from S3:
   ```bash
   aws --endpoint-url "$S3_ENDPOINT_URL" s3 cp \
       "s3://$S3_BUCKET/pg/$(aws --endpoint-url $S3_ENDPOINT_URL s3 ls s3://$S3_BUCKET/pg/ | sort | tail -1 | awk '{print $4}')" \
       /var/backups/enigmatrix/pg/restore.dump
   aws --endpoint-url "$S3_ENDPOINT_URL" s3 cp \
       "s3://$S3_BUCKET/chroma/$(aws --endpoint-url $S3_ENDPOINT_URL s3 ls s3://$S3_BUCKET/chroma/ | sort | tail -1 | awk '{print $4}')" \
       /var/backups/enigmatrix/chroma/restore.tar.gz
   ```
4. Decrypt secrets and `git clone` the repo at the SHA recorded in `/etc/enigmatrix/last_deployed_sha` (also mirrored to S3). (~2 min)
5. `docker compose pull && docker compose up -d postgres chromadb redis`. Wait for healthchecks. (~3 min)
6. Restore pg_dump and chroma archive per §7.3. (~8 min)
7. Bring up the rest: `docker compose up -d`. (~2 min)
8. Issue a fresh TLS certificate or restore the `letsencrypt` volume from the most recent pre-restore S3 mirror. (~3 min)
9. Smoke test: `/health`, login flow, one document ingest. (~2 min)

Wall-clock target: ~32 minutes; rehearsed quarterly via a DR drill that restores into a throwaway VM and runs the smoke tests automatically.

### 10.2 Postgres-only corruption

`pg_restore` directly into the running cluster (after stopping consumers). Approx 8 minutes for a 5 GB dump.

### 10.3 Chroma-only corruption

Stop chromadb, replace the volume contents with the latest `chroma-*.tar.gz`, restart. Approx 5 minutes. Backend tolerates a temporarily missing collection by returning an explicit `503 vector_store_unavailable`.

---

## Acceptance Criteria

1. `docker compose up -d` on a clean VM brings every service to a `healthy` status within 60 seconds (excluding initial image pull).
2. nginx serves `https://enigmatrix.app` with a valid Let's Encrypt certificate; HTTP requests are 301-redirected to HTTPS; HSTS header present.
3. The auth rate-limit zone (`5 req/s`, burst 10) returns HTTP 429 under a synthetic flood test; the general `/api/` zone tolerates 30 req/s.
4. Total resident memory for the stack stays under 14 GB during a load test of 50 concurrent users; no OOM kills observed for 24 hours.
5. `pg_dump.sh` runs nightly via cron and produces a non-empty `enigmatrix-*.dump` whose `pg_restore --list` succeeds; the previous Sunday's dump is present in S3.
6. `chroma_snapshot.sh` runs nightly and produces a non-empty tarball mirrored to S3; restoring it into a scratch container reopens every collection.
7. `infra/deploy/promote.sh blue` and `... green` both succeed end-to-end in under two minutes, including nginx reload and old-colour drain.
8. The GitHub Actions `deploy` workflow builds and pushes all three images to GHCR on every push to `main`, and the deploy job updates the candidate colour using the commit SHA as the image tag.
9. A scheduled DR drill (run quarterly) restores a fresh VM from the latest S3 backups and passes smoke tests in under 30 minutes.
10. `.env.example` lists every secret consumed in this build; the live `.env` on the VM is mode 0600 and never appears in any image layer (`docker history` audit clean).

---

## Claude Prompts

**(a) Backend Dockerfile + compose service.**
"Write a multi-stage `apps/backend/Dockerfile` for an Enigmatrix FastAPI app using `python:3.11-slim` and `uv` with `uv.lock` in frozen mode, producing a non-root runtime image with a `/health` HEALTHCHECK and gunicorn launching two `uvicorn.workers.UvicornWorker`. Then emit the matching `backend` service block for `docker-compose.yml` with healthcheck, env_file layering, depends_on conditions on postgres, redis, and chromadb, and a 2 GB / 1 vCPU resource limit. Do not include torch."

**(b) nginx config.**
"Generate `infra/nginx/enigmatrix.conf` that terminates TLS for `enigmatrix.app`, redirects HTTP to HTTPS, sets an HSTS header with `max-age=63072000; includeSubDomains; preload`, defines two `limit_req_zone`s (`auth_zone` 5 r/s and `api_zone` 30 r/s), proxies `/api/v1/auth/*` through `auth_zone`, the rest of `/api/*` through `api_zone`, `/annotate/` to Label Studio behind basic-auth, and `/` to the Next.js frontend. Include keepalive upstreams and a `/.well-known/acme-challenge/` location for certbot."

**(c) GitHub Actions deploy workflow.**
"Write `.github/workflows/deploy.yml` that on push to `main` builds three images (backend, frontend, ml-worker) with `docker/build-push-action`, pushes them to GHCR tagged with both `${{ github.sha }}` and `latest`, and then in a gated `production` environment ssh-deploys to the VM. Use OIDC where possible (`permissions: id-token: write`) and fall back to an SSH key in `secrets.DEPLOY_SSH_KEY`. The remote step must read the active colour from `/etc/enigmatrix/active`, deploy to the opposite colour with `IMAGE_TAG=${{ github.sha }}`, and run `infra/deploy/promote.sh` to switch nginx."

---

**Prev:** BUILD_13_Admin_and_Annotation.md  ·  **Next:** BUILD_15_Observability_Testing.md
