---
title: Runtime and Deployment Inventory
document: inventory/runtime-and-deployment
version: 0.1.0
status: Draft
phase: 0
source_repository: https://github.com/ohcnetwork/care
source_branch: gcp
source_commit: 6a2976dc2512c2c532fcc70628c5690fbbbe3f3d
reviewed: 2026-08-05
---

# Runtime and Deployment Inventory

How CARE is built, started and tested today, plus the Phase 0 baseline command
attempt. Nothing in the runtime was modified in this phase.

Evidence labels: **verified** / **inferred** / **unknown**.

---

## 1. Process commands

**verified** Five entrypoint scripts define every process CARE runs.

| Process | Script | Command | Used by |
| --- | --- | --- | --- |
| API (prod) | `scripts/start.sh` | `gunicorn --config python:config.gunicorn config.wsgi:application --bind 0.0.0.0:9000 --chdir=/app --workers $GUNICORN_WORKERS` | `docker/prod.Dockerfile` |
| API (dev) | `scripts/start-dev.sh` | `python manage.py runserver_plus 0.0.0.0:9000 --print-sql` | `docker-compose.local.yaml:13` |
| Worker (prod) | `scripts/celery_worker.sh` | `celery --app=config.celery_app worker --max-tasks-per-child=6 --loglevel=info --concurrency=${CELERY_WORKER_CONCURRENCY:-1}` | — |
| Beat (prod) | `scripts/celery_beat.sh` | `celery --app=config.celery_app beat --loglevel=info` | — |
| Worker+Beat (dev) | `scripts/celery-dev.sh` | `watchmedo auto-restart ... celery ... worker -B --loglevel=INFO` | `docker-compose.local.yaml:30` |

**verified** ECS variants also exist: `scripts/start-ecs.sh`,
`scripts/celery_worker-ecs.sh`, `scripts/celery_beat-ecs.sh`.

**verified** `scripts/celery-dev.sh` runs `worker -B` — worker and beat in one
process. `scripts/celery_worker.sh` and `scripts/celery_beat.sh` separate them.

**verified** `Procfile` describes a third shape entirely:

```
web: gunicorn config.wsgi:application
release: python manage.py collectstatic --noinput && python manage.py migrate
```

**verified** The `Procfile` `release` phase is the **only** place in the
repository where migrations are tied to a deploy step rather than to a
long-running process. It defines no worker.

---

## 2. Migration behavior

**verified** This is the single most important runtime fact for Cloud Run.

| Script | Runs `migrate`? | Line |
| --- | --- | --- |
| `scripts/start.sh` (API, prod) | **no** | — |
| `scripts/start-dev.sh` (API, dev) | **no** | — |
| `scripts/celery_worker.sh` | **no** | — |
| `scripts/celery_beat.sh` | **yes** | `python manage.py migrate --noinput` |
| `scripts/celery-dev.sh` | **yes** | `python manage.py migrate --noinput` |
| `Procfile` | yes, as `release` | line 2 |

**verified** In the Docker-based deployment, **schema migration is a side effect
of starting Celery Beat**. The API container never migrates.

**verified** `scripts/celery_beat.sh` and `scripts/celery-dev.sh` also run two
data-seeding commands after migrating:

```
python manage.py sync_permissions_roles
python manage.py sync_valueset
```

**verified** `care/security/management/commands/sync_permissions_roles.py:14`
documents that concurrent runs are *"automatically blocked with redis"* — i.e.
this startup step depends on the distributed lock described in
`cache-and-redis.md` §4.2.

**inferred** Cloud Run has no beat process. Migrations and both sync commands
need an explicit home — a Cloud Run Job or a deploy step — or they will never
run. This is not a refactor; it is a gap that appears the moment beat is removed.

---

## 3. Startup dependencies

**verified** Every prod and dev entrypoint waits for **both** PostgreSQL and
Redis before starting:

| Script | `wait_for_db.sh` | `wait_for_redis.sh` |
| --- | --- | --- |
| `scripts/start.sh` | yes | **yes** |
| `scripts/start-dev.sh` | yes | **yes** |
| `scripts/celery_worker.sh` | yes | yes |
| `scripts/celery_beat.sh` | yes | yes |
| `scripts/celery-dev.sh` | yes | yes |

**verified** The API blocks on Redis at startup even though its only Redis use is
the cache and the token denylist.

**inferred** On Cloud Run this is a cold-start blocker: an instance cannot serve
until Redis answers. Combined with `IGNORE_EXCEPTIONS: True`
(`config/settings/base.py:93`), the runtime is inconsistent — it refuses to
*start* without Redis but silently tolerates Redis failing later.

**verified** `scripts/start.sh`, `celery_worker.sh` and `celery_beat.sh` all
synthesize connection URLs when unset:

```bash
export DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
export REDIS_URL="rediss://:${REDIS_AUTH_TOKEN}@${REDIS_HOST}:${REDIS_PORT}/${REDIS_DATABASE}?ssl_cert_reqs=none"
```

**verified** The Redis URL uses the TLS scheme `rediss://` with
`ssl_cert_reqs=none` — TLS without certificate verification.

---

## 4. Static files and i18n

**verified** `collectstatic --noinput` runs **at container start**, not at image
build time:

| Script | Line |
| --- | --- |
| `scripts/start.sh` | `python manage.py collectstatic --noinput` |
| `scripts/start-dev.sh` | same |
| `scripts/celery_worker.sh` | same |

**verified** `compilemessages -v 0` runs at start in all five scripts.

**verified** `whitenoise` is a dependency (`Pipfile`, `whitenoise = "==6.11.0"`),
so static files are served from the application process.

**inferred** Running `collectstatic` and `compilemessages` on every cold start
adds latency to every Cloud Run instance launch and repeats identical work.
Moving both into the image build is a contained, low-risk improvement.

**verified** `scripts/celery_worker.sh` runs `collectstatic` even though a worker
serves no HTTP.

---

## 5. Health checks

**verified** `docker/prod.Dockerfile:65-70` declares:

```
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=12 CMD ["./healthcheck.sh"]
```

**verified** `scripts/healthcheck.sh` dispatches on a role file written by each
entrypoint to `/tmp/container-role`:

| Role | Probe |
| --- | --- |
| `api` | `curl -fsS http://localhost:9000/ping/` |
| `celery-beat` | `ls /tmp/healthy` — a marker file touched before beat starts |
| `celery*` | `celery -A config.celery_app inspect ping -d celery@$HOSTNAME` |

**verified** Roles are written at the top of each script: `api`
(`start.sh`, `start-dev.sh`), `celery` (`celery-dev.sh`), `celery-worker`
(`celery_worker.sh`), `celery-beat` (`celery_beat.sh`).

**verified** The beat health check is a **liveness lie**: `touch /tmp/healthy`
happens *before* `celery beat` is exec'd in `scripts/celery_beat.sh`, so the file
persists even if beat dies.

**verified** The application-level health config is `HEALTHY_DJANGO` at
`config/settings/base.py:453-467`, with three probes: database, cache, and Celery
queue length. See `cache-and-redis.md` §4.9 — the third connects directly to
Redis and is meaningless under Cloud Tasks.

**inferred** For Cloud Run, only the `api` branch is relevant; `/ping/` is the
natural startup and liveness probe.

---

## 6. Images

**verified** Two Dockerfiles: `docker/dev.Dockerfile` and `docker/prod.Dockerfile`.

**verified** `docker/prod.Dockerfile` structure:

| Stage | Lines | Purpose |
| --- | --- | --- |
| `base` | 1-15 | `python:3.13-slim-bookworm`, env setup |
| `builder` | 19-39 | build deps, `pipenv install --deploy --categories "packages"`, plugin install |
| `runtime` | 42-72 | runtime deps, non-root `django` user, venv copy, healthcheck |

**verified** Notable facts:

- Base image `python:3.13-slim-bookworm` (`:1`) — matches `Pipfile`'s
  `python_version = "3.13"`.
- Runs as non-root `django` (`:44-45`, `:63`).
- `EXPOSE 9000` (`:72`).
- **No `CMD` or `ENTRYPOINT`.** The image declares neither; the orchestrator must
  supply the command. **inferred** Cloud Run requires an explicit container
  command, so each service must set it.
- WeasyPrint native deps (`libpango`, `libharfbuzz`) installed in both stages
  (`:23`, `:48`) — these are what make report generation work.
- Plugins are installed **at image build time** (`:34-39`) via
  `install_plugins.py`, parameterized by the `ADDITIONAL_PLUGS` build arg
  (`:37-38`).

**verified** The `CMD` entries at `docker/prod.Dockerfile:70` and
`docker/dev.Dockerfile:36` are the **`HEALTHCHECK` `CMD`**, not a container
command. Neither image declares a top-level `CMD` or `ENTRYPOINT`.

### 6.1 Production image availability

**verified** `.github/workflows/deploy.yml` publishes a production image:

| Fact | Evidence |
| --- | --- |
| Registry | `ghcr.io/${{ github.repository }}` → `ghcr.io/ohcnetwork/care` (`deploy.yml:64, 97`) |
| Dockerfile | `docker/prod.Dockerfile` (`deploy.yml:94`) |
| Architectures | `linux/amd64` + `linux/arm64` (`deploy.yml:44-49`) |
| Push mode | `push-by-digest=true,name-canonical=true,push=true` (`deploy.yml:97`) |
| Triggers | tags `v*`, pushes to `develop`, manual dispatch (`deploy.yml:3-11`) |
| Gate | `github.repository == 'ohcnetwork/care'` (`deploy.yml:31`) |

**inferred** A ready-made multi-arch production image exists upstream, so a GCP
deployment can consume `ghcr.io/ohcnetwork/care` directly rather than building
one — provided it supplies its own container command (§6) and its own migration
step (§2). Note the fork's images are **not** published: the gate at
`deploy.yml:31` restricts the job to the upstream repository.

**verified** The ECS deployment env block in `deploy.yml:19-29` is **entirely
commented out**, as is a further block at `deploy.yml:207-209`. **inferred** the
ECS deploy path is currently inactive upstream.

---

## 7. Compose topology

**verified** `docker-compose.yaml` defines three infrastructure services:

| Service | Image | Host port | Healthcheck |
| --- | --- | --- | --- |
| `db` | `postgres:17-alpine` | 5433→5432 | `pg_isready` |
| `redis` | `redis:8-alpine` | 6380→6379 | `redis-cli ping` |
| `minio` | `minio/minio:latest` | 9100→9000, 9001 | `/minio/health/ready` |

**verified** `docker-compose.local.yaml` adds `backend` and `celery`, both from
the `care_local` image built from `docker/dev.Dockerfile`.

**verified** `backend` depends on `celery` with `condition: service_healthy`
(`docker-compose.local.yaml:23-24`). **inferred** this ordering exists because
`celery-dev.sh` runs the migrations — the API waits for the schema.

**verified** MinIO buckets are created by `docker/minio/init-script.sh`, which
also sets them **public**: `mc anonymous set public local/$BUCKET_NAME`
(`init-script.sh:47`).

**verified** PostgreSQL in compose is **17**; the target described in the
architecture docs is Cloud SQL. Version parity is a deployment decision, not a
code constraint.

**verified** Additional compose files: `docker-compose.pre-built.yaml` and
`docker-compose.coolify.yaml`.

---

## 8. CI

**verified** `.github/workflows/` contains 8 workflows: `deploy.yml`, `docs.yml`,
`linter.yml`, `release.yml`, `reusable-test.yml`, `test-merge-queue.yml`,
`test-pull-request.yml`, `validate-pr-title.yml`.

**verified** `reusable-test.yml` is the test pipeline. Its ordered steps:

| Step | Command | Line |
| --- | --- | --- |
| Build image | `docker buildx build --file docker/dev.Dockerfile --tag care_local ... --platform linux/arm64` | 52-59 |
| Start services | `docker compose -f docker-compose.yaml -f docker-compose.local.yaml up -d --wait` | 63 |
| Check migrations | `make checkmigration` | 67 |
| Fixtures | `make load-fixtures` | 70 |
| Tests | `make test-coverage` | 77 |

**verified** Runner is `ubuntu-24.04-arm` (`:17`); CI builds and tests
**arm64 only** (`:57`).

**verified** `make checkmigration` → `python manage.py makemigrations --check --dry-run`
(`Makefile:47-48`). CI fails on uncommitted model changes.

**verified** `make test-coverage` → `coverage run manage.py test --settings=config.settings.test --keepdb --parallel --shuffle` (`Makefile:63-66`).

**verified** `config/settings/test.py:45-46` points the cache at
`django_redis.cache.RedisCache` on `REDIS_URL`, so **CI requires a live Redis**.

---

## 9. Dependencies

**verified** Manager: **Pipenv** (`Pipfile` + `Pipfile.lock`). No
`requirements.txt`, no Poetry, no uv.

**verified** Key pins:

| Package | Version | Relevance |
| --- | --- | --- |
| `python_version` | `3.13` | `Pipfile [requires]` |
| `django` | `==6.0` | |
| `celery` | `==5.6.0` | |
| `django-redis` | `==6.0.0` | supplies `delete_pattern`, `nx=`, `get_redis_connection` |
| `redis` | `==7.1.0` (extras `hiredis`) | |
| `boto3` | `==1.43.6` | only S3 client today |
| `psycopg` | `==3.3.2` (extras `c`) | |
| `gunicorn` | `==23.0.0` | |
| `whitenoise` | `==6.11.0` | |
| `django-ratelimit` | `==4.1.0` | |
| `healthy-django` | `==0.1.0` | |
| `weasyprint` | `==68.0` | report rendering |
| `drf-spectacular` | `==0.29.0` | |
| `sentry-sdk` | `==2.58.0` | |

**verified** `pyproject.toml:22` sets `requires-python = "==3.13.*"` and
`pyproject.toml:58` sets ruff `target-version = "py313"`.

**verified** **Absent** from `Pipfile`: `django-storages`, any
`google-cloud-*` package, `django-celery-beat`, `django-celery-results`.

**verified** `django-anymail` is installed with the `amazon-ses` extra.
**inferred** email delivery is AWS SES today; GCP has no drop-in equivalent, so
this needs an explicit decision.

---

## 10. Existing GCP-related code

**verified** A repository-wide search for `gcp`, `google.cloud`, `cloud run`,
`cloudsql`, `cloud_tasks`, `django-storages` and `django_storages` across
`*.py`, `*.yml`, `*.yaml`, `*.sh`, `Pipfile` and `*.toml`, excluding
`docs/xii/`, returns exactly **two** matches:

| File | Line | Content |
| --- | --- | --- |
| `care/utils/csp/config.py` | 20 | `GCP = "GCP"` — a `CSProvider` enum member |
| `care/emr/utils/file_manager.py` | 130 | `# bulk delete is not supported by some providers: GCP` |

**verified** The `CSProvider.GCP` member is **never branched on**.
`BUCKET_PROVIDER` is only ever compared against `CSProvider.AWS_ROLE_BASED`
(`care/utils/csp/config.py:35, 48, 62`).

**verified** There is no Terraform, no Cloud Build config, no `app.yaml`, no
`service.yaml`, and no GCP credentials handling anywhere in the repository.

**Conclusion (verified):** GCP support does not exist. This is genuinely
greenfield.

---

## 11. Baseline command results

**Status: BLOCKED — no baseline could be recorded.**

The prompt asked for the safest available equivalents of `make build`, `make up`,
`make load-fixtures` and `make test`. The official commands were discovered from
`Makefile:19-20, 25-26, 38-39, 56-57` and are:

```bash
make build          # docker compose -f docker-compose.yaml -f docker-compose.local.yaml build
make up             # docker compose -f docker-compose.yaml -f docker-compose.local.yaml up -d --wait
make load-fixtures  # docker compose exec backend bash -c "python manage.py load_fixtures"
make test           # docker compose exec backend bash -c "python manage.py test  --keepdb --parallel --shuffle"
```

**None were executed.** No destructive command was run; no volume was removed; no
database was reset.

### 11.1 Blockers

| # | Blocker | Evidence | Effect |
| --- | --- | --- | --- |
| B1 | **Docker daemon not running** | `docker info` → `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine ... El sistema no puede encontrar el archivo especificado` | All four `make` targets unavailable — every one shells out to `docker compose` |
| B2 | **`make` not installed** | `make --version` → `bash: line 1: make: command not found` | Targets cannot be invoked by name even with Docker up |
| B3 | **No Python environment** | no `.venv` directory; `pipenv --version` → command not found; `python -c "import django"` → `ModuleNotFoundError: No module named 'django'` | The documented non-Docker fallback in `CLAUDE.md` is unavailable |
| B4 | **Host Python version mismatch** | host `python --version` → **3.14.5**; `pyproject.toml:22` requires `==3.13.*` | Even building a venv by hand would violate the project constraint |
| B5 | **Redis not running** | TCP connect to `localhost:6379` refused | `config/settings/test.py:45-46` requires Redis; tests would fail regardless |

### 11.2 What is available

| Check | Result |
| --- | --- |
| `docker --version` | `Docker version 29.5.2, build 79eb04c` — client present, daemon down |
| `docker compose version` | `Docker Compose version v5.1.4` |
| PostgreSQL on `localhost:5432` | port **open** |
| `psql` client | not on PATH — server version unverified |
| `ruff` | not on PATH |
| `.env` | **absent** (`.env.example` present) |

**verified** Note that a listening PostgreSQL on 5432 is not the compose
database — `docker-compose.yaml:16` maps the compose `db` to host port **5433**.
The process on 5432 is a host-local PostgreSQL of **unknown** version and
contents. It was not connected to, queried or modified.

### 11.3 To unblock

**inferred** — the minimum to record a real baseline:

1. Start Docker Desktop (resolves B1).
2. Invoke the underlying `docker compose` commands directly, or install `make`
   (resolves B2).
3. `cp .env.example .env` — `Makefile` and compose both expect it.

Steps 1-3 make B3, B4 and B5 irrelevant, since all execution then happens inside
the container with the correct Python and a compose-provided Redis.

**Not attempted deliberately:** starting Docker Desktop, installing `make`,
creating `.env`, or provisioning a Python 3.13 toolchain. Each modifies the
developer environment beyond the read-only scope of Phase 0.

### 11.4 Baseline record

| Field | Value |
| --- | --- |
| Command | none executed |
| Success / failure | n/a — not run |
| Duration | n/a |
| Test count | **unknown** |
| Failures | **unknown** |
| Skipped | **unknown** |
| Unhealthy services | **unknown** |
| Logs | none produced |

**This table must be filled before any migration work begins.** Without a green
baseline there is no reference point to attribute later failures to.

---

## 12. Runtime facts most relevant to Cloud Run

**verified**, ordered by how much they constrain the design:

1. **Migrations run only in Celery Beat startup** (§2). Removing beat removes
   migrations.
2. **`sync_permissions_roles` and `sync_valueset` run at beat startup** (§2) and
   the first depends on a Redis lock.
3. **The API blocks on Redis before serving** (§3).
4. **The prod image declares no `CMD`** (§6). Every Cloud Run service must set one.
5. **`collectstatic` and `compilemessages` run per cold start** (§4).
6. **Celery timezone is hardcoded to `Asia/Kolkata`** (`config/celery_app.py:16`);
   any Cloud Scheduler translation must account for IST.
7. **The Celery queue-length health check binds to Redis** (§5).
8. **CI builds arm64 only** (§8); Cloud Run defaults to amd64.
9. **`django-anymail[amazon-ses]`** (§9) ties email to SES.
