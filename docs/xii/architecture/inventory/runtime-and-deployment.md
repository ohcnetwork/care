---
title: Runtime and Deployment Inventory
document: inventory/runtime-and-deployment
version: 0.2.0
status: Draft
phase: 0
source_repository: https://github.com/ohcnetwork/care
source_branch: gcp
source_commit: 6a2976dc2512c2c532fcc70628c5690fbbbe3f3d
baseline_commit: 2fe40cd16
reviewed: 2026-08-06
---

# Runtime and Deployment Inventory

How CARE is built, started and tested today, plus the Phase 0 runtime baseline
(§11). Nothing in the runtime was modified in this phase.

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

```text
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

```bash
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

**Recommend** treating this as a defect to fix, not a baseline to carry forward.
`ssl_cert_reqs=none` encrypts the connection but authenticates nothing, so it
stops passive sniffing and not an active man-in-the-middle — which is most of
what TLS to a managed Redis endpoint is for. The target runtime SHALL verify
against the deployment CA (`ssl_cert_reqs=required` plus `ssl_ca_certs`, or the
system trust store where the provider uses a public CA). If verification must be
disabled anywhere, it SHALL be scoped to local development, where the endpoint
is a container on a private network and there is no CA to verify against.

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

```dockerfile
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

**Superseded by IS-01 for the first two.** `Pipfile:55` now carries
`django-storages = {extras = ["s3", "google"], version = "==1.14.6"}`, which
brings `google-cloud-storage` in transitively. `django-celery-beat` and
`django-celery-results` remain absent.

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

**Superseded by IS-01.** Both rows above are gone: `care/utils/csp/config.py` was
deleted with the provider-specific bucket configuration, and the `file_manager.py`
bulk-delete comment went with the boto3 code. Re-running the same search now
returns matches in `config/storage.py`, `config/settings/base.py`,
`care/utils/tests/test_storage_config.py` and `Pipfile` — the `gcs` backend
option and its tests.

The conclusion still holds for everything outside storage: there is still no
Terraform, no Cloud Build config, no `app.yaml`, no `service.yaml` and no GCP
credentials handling. Storage is the one axis where GCP is now selectable, and
selecting it is a settings change rather than a code change.

---

## 11. Baseline command results

**Status: GREEN.** Recorded 2026-08-06. The blockers listed in the previous
revision of this section are resolved; the record below supersedes them.

No destructive command was run: no volume was removed, no database was reset, no
container or image existed before the run. `docker volume ls`, `docker ps -a` and
`docker images` were all empty at the start, so every artifact below was created
by this baseline.

### 11.1 Environment

| Field | Value |
| --- | --- |
| Operating system | Microsoft Windows 11 Pro, version 10.0.26200 |
| Shell | PowerShell 5.1.26100.8875; Git Bash for the `docker compose` invocations |
| Docker Engine | client **29.6.2**, server **29.6.2** (Docker Desktop, WSL2 backend) |
| Docker Compose | **v5.3.1** |
| Container kernel | `Linux-6.6.114.1-microsoft-standard-WSL2-x86_64-with-glibc2.36` |
| Repository branch | `feature/gcp-phase-0-inventory` |
| Repository commit | `2fe40cd16` |
| Working tree | clean before and after |
| Python in image | 3.13.14 |
| Django in image | 6.0 |
| Plugins | none — `plug_config.py` declares `plugs = []`, `ADDITIONAL_PLUGS` unset |

**verified** Docker Desktop upgraded its own components when it was launched: the
CLI reported `29.5.2` / Compose `v5.1.4` before the daemon started and
`29.6.2` / `v5.3.1` afterwards. The versions in the table are the ones the
baseline actually ran on.

### 11.2 Environment files

**verified** No gitignored environment file had to be created. This corrects the
previous revision, which listed a missing `.env` as a blocker.

| File | Status | Role |
| --- | --- | --- |
| `docker/.local.env` | **tracked in git** | `env_file` for `backend` and `celery` (`docker-compose.local.yaml:10, 29`) |
| `docker/.prebuilt.env` | **tracked in git** | `env_file` for `db` (`docker-compose.yaml:11`) |
| `.env` (repository root) | gitignored, **absent, not required** | — |

**verified** There is no `docker/.local.env.example` and no
`docker/.prebuilt.env.example`. The two `.env` files are the real, committed
artifacts, not templates.

**verified** `docker compose config` resolves with **no** missing-variable
warnings without a root `.env`. Every interpolation in the compose files supplies
a default: `BACKUP_DIR` (`docker-compose.yaml:14`), `MINIO_ACCESS_KEY` and
`MINIO_SECRET_KEY` (`:42-43`), `POSTGRES_USER` (`:18`), and `ADDITIONAL_PLUGS`
(`docker-compose.local.yaml:8`).

**verified** Compose v5.3.1 interpolates values *inside* `env_file`. The literal
`BUCKET_KEY=${MINIO_ACCESS_KEY:-minioadmin}` at `docker/.local.env:14` arrives in
the container as `BUCKET_KEY=minioadmin`. Confirmed by reading the resolved
environment inside `backend`.

### 11.3 Commands executed

**verified** GNU Make is not installed on this host, so each `Makefile` target
was translated to the exact `docker compose` command it wraps. File order and
flags are unchanged from the `Makefile`.

| Step | `Makefile` target | Command executed |
| --- | --- | --- |
| Build | `build` (`:19-20`) | `docker compose -f docker-compose.yaml -f docker-compose.local.yaml build` |
| Start + wait | `up` (`:25-26`) | `docker compose -f docker-compose.yaml -f docker-compose.local.yaml up -d --wait` |
| Service state | `list` (`:41-42`) | `docker compose -f docker-compose.yaml -f docker-compose.local.yaml ps` |
| Migration check | `checkmigration` (`:47-48`) | `docker compose exec backend bash -c "python manage.py makemigrations --check --dry-run"` |
| Fixtures | `load-fixtures` (`:38-39`) | `docker compose exec backend bash -c "python manage.py load_fixtures"` |
| Tests | `test` (`:56-57`) | `docker compose exec backend bash -c "python manage.py test  --keepdb --parallel --shuffle"` |

**verified** The four `exec` targets in the `Makefile` pass **no** `-f` flags, so
they rely on Compose's default file resolution — which finds only
`docker-compose.yaml`, where `backend` is not defined. This works anyway:
Compose v5 `exec` resolves the container by project label (project name `care`,
derived from the directory), not by service presence in the loaded config.
Confirmed empirically — `docker compose exec backend bash -c "echo OK"` succeeds.
**inferred** This is an implicit dependency on Compose's lookup behaviour rather
than an intentional design, but it is not currently broken.

### 11.4 Build result

**verified** `care_local:latest` built successfully.

| Field | Value |
| --- | --- |
| Image | `care_local:latest` |
| Manifest list digest | `sha256:4ea640b476e9050288e7f98899d848a987339e56e78ff3c4b75b3a96a8b6f70b` |
| Size | 1.6 GB |
| Platform | `linux/amd64` |
| Dockerfile | `docker/dev.Dockerfile` |

**The first build attempt failed.** Classified as a **dependency-build** failure,
not an application defect:

```text
zipfile.BadZipFile: Bad CRC-32 for file '_brotli.cpython-313-x86_64-linux-gnu.so'
ERROR: Couldn't install package: {}
failed to solve: process "/bin/sh -c pipenv  install --system --categories \"packages dev-packages docs\""
  did not complete successfully: exit code: 1
```

A corrupted wheel had been written into the BuildKit pip cache mount declared at
`docker/dev.Dockerfile:22`. Because the cache mount persists across builds, a
plain retry would have reused the same corrupt file. The minimum correction was
to drop only the cache mounts —
`docker builder prune --filter type=exec.cachemount` (92.29 MB, all of it created
minutes earlier by that same failed build). No volume, container or image was
touched. The rebuild succeeded and the failure has not recurred. **inferred**
transient; no source change was made or needed.

### 11.5 Service health

**verified** All five services reached `healthy` under `up -d --wait`, and were
still healthy an hour later.

| Service | Container | Health | Ports |
| --- | --- | --- | --- |
| `db` | `care-db-1` | healthy | 5433→5432 |
| `redis` | `care-redis-1` | healthy | 6380→6379 |
| `minio` | `care-minio-1` | healthy | 9100→9000, 9001→9001 |
| `celery` | `care-celery-1` | healthy | — |
| `backend` | `care-backend-1` | healthy | 9000→9000, 9876→9876 |

**verified** `curl http://localhost:9000/ping/` inside `backend` returns
`{"status": "OK"}`.

### 11.6 Startup sequence

**verified** from container logs, in order.

`celery` (`scripts/celery-dev.sh`):

| Step | Evidence |
| --- | --- |
| Waited for PostgreSQL | `Waiting for PostgreSQL to become available...` ×2, then `PostgreSQL is available` |
| Waited for Redis | `Redis is available` |
| Ran migrations | `Running migrations:` — **312** `Applying ... OK` lines across `admin, auth, authtoken, contenttypes, emr, facility, security, sessions, sites, users` |
| Ran `sync_permissions_roles` | no stdout; verified by effect (§11.7) |
| Ran `sync_valueset` | no stdout; verified by effect (§11.7) |
| Worker started | banner `celery@b2c90b2c6f0b v5.6.0`, `concurrency: 16 (prefork)`, `transport: redis://redis:6379/0`, 8 registered tasks, `Connected to redis://redis:6379/0` |
| Beat started | `worker -B`; `/app/celerybeat-schedule`, `-shm` and `-wal` present and being written |

`backend` (`scripts/start-dev.sh`):

| Step | Evidence |
| --- | --- |
| Waited for PostgreSQL | `PostgreSQL is available` |
| Waited for Redis | `Redis is available` |
| `collectstatic` | `198 static files copied to '/app/staticfiles', 926 post-processed.` |
| Server started | `starting server...`, health check passing on `/ping/` |

**verified** The database did not exist beforehand; `scripts/wait_for_db.sh`
created it (`Creating Database` path) before migrations ran.

**verified — minor logging gap.** The `celery` log ends at
`mingle: all alone` and never emits the usual `celery@<host> ready.` line, nor
any `beat: Starting...` line. The worker is nonetheless live —
`celery -A config.celery_app inspect ping` returns `1 node online` — and beat is
live, evidenced by the schedule files above. **inferred** log truncation under
`watchmedo auto-restart`, not a process failure. Recorded so that a future reader
does not mistake the missing lines for a broken worker.

### 11.7 Migration and synchronization results

| Check | Result |
| --- | --- |
| `migrate` | **312** migrations applied, 0 errors |
| `makemigrations --check --dry-run` | `No changes detected` — no model drift |
| `sync_permissions_roles` | `security_permissionmodel` = **115**, `security_rolemodel` = **10**, `security_rolepermission` = **546** |
| `sync_valueset` | `emr_valueset` = **30** |

**verified** Neither sync command prints to stdout. Both run under
`set -euo pipefail` in `scripts/celery-dev.sh`, so a failure would have aborted
container startup; their success is additionally confirmed by the row counts
above, queried directly from `care-db-1`.

### 11.8 Fixture result

**verified** `python manage.py load_fixtures` completed successfully:
`All fixtures loaded successfully!`

Seventeen fixture groups loaded — organizations, facility, departments,
locations, devices, users, patients, encounters, facility organization
memberships, secondary facility, questionnaires, report templates, lab
definitions, inventory, billing, scheduling, managing organization.

Resulting counts: `users_user` = 10, `facility_facility` = 2,
`emr_organization` = 12. Ten test accounts are printed by the command; the
credentials are development-only and are not reproduced here.

### 11.9 Test results

**verified** Command:
`docker compose exec backend bash -c "python manage.py test  --keepdb --parallel --shuffle"`

Settings module is `config.settings.test`, selected automatically by
`manage.py:15-16`. `--parallel` used **16** workers (17 test databases including
the primary).

| Run | Shuffle seed | Tests | Pass | Fail | Skip | Test duration | Wall clock | Exit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 8926493199 | 1912 | 1911 | 1 | 0 | 22.296 s | 138 s | 1 |
| 2 | 8078922123 | 1912 | 1912 | 0 | 0 | 29.482 s | 48 s | 0 |
| 3 | 3975608265 | 1912 | 1912 | 0 | 0 | 21.158 s | 37 s | 0 |

**Test count: 1912. Skipped: 0. Expected failures: 0. Warnings: none emitted by
the test runner.**

Run 1's longer wall clock includes first-time creation of the 17 test databases;
runs 2 and 3 reused them via `--keepdb`.

**Baseline verdict: green.** Two of three runs are fully clean; the single
failure in run 1 is a test-isolation flake in the suite itself, characterised
below, not a defect in the application under test.

### 11.10 Known defect — flaky rate-limit test

**verified** Run 1 failed one test:

```text
care/emr/tests/test_reset_password_api.py:375
  ResetPasswordAPITest.test_password_request_rate_limiting
AssertionError: 200 != 429
```

**verified** It passes deterministically in isolation, both as a single test and
as the whole module, run serially:
`python manage.py test care.emr.tests.test_reset_password_api --keepdb` → `Ran 23 tests ... OK`.

**verified** Mechanism — two facts combine:

1. `config/ratelimit.py:9`, `get_ratelimit_key`, returns the **constant** string
   `"ratelimit"`. The rate-limit counter is therefore process-global: it is not
   keyed by IP, user or test.
2. `config/settings/test.py:45-56` points the cache at **Redis**, shared by all
   16 parallel workers under a single `KEY_PREFIX` of `test_`. Meanwhile
   `cache.clear()` runs in `setUp` at `care/emr/tests/test_reset_password_api.py:24`
   and `care/emr/tests/test_valueset_api.py:23, 52`.

**inferred** A concurrent worker calling `cache.clear()` wipes the shared global
counter partway through the test's 11-request loop, so the final request returns
200 instead of 429. `--shuffle` decides whether the interleaving happens, which
is why the failure is intermittent.

**Not fixed.** This is a pre-existing upstream test-isolation defect, unrelated to
GCP work, and fixing it would be an application change outside the scope of
recording a baseline. It is reproducible in principle on upstream CI, which runs
the same `--parallel --shuffle` combination via `make test-coverage`
(`.github/workflows/reusable-test.yml:77`).

**inferred, relevant to the target runtime:** the global rate-limit key is also a
correctness concern beyond tests — it means the limit is shared across all
callers, not per client. Recorded here as an observation only.

### 11.11 Reproducing this baseline

```bash
# 1. build
docker compose -f docker-compose.yaml -f docker-compose.local.yaml build

# 2. start and wait for health
docker compose -f docker-compose.yaml -f docker-compose.local.yaml up -d --wait

# 3. confirm state
docker compose -f docker-compose.yaml -f docker-compose.local.yaml ps

# 4. migrations already ran in the celery container; confirm no drift
docker compose exec backend bash -c "python manage.py makemigrations --check --dry-run"

# 5. fixtures
docker compose exec backend bash -c "python manage.py load_fixtures"

# 6. tests
docker compose exec backend bash -c "python manage.py test  --keepdb --parallel --shuffle"
```

No `.env` file is needed. No teardown, volume deletion or database reset is
required or advised — `make teardown` (`Makefile:34-35`) and `make reset-db`
(`:76-78`) are destructive and were deliberately not used.

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
