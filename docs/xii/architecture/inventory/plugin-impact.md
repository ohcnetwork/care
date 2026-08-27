---
title: Plugin Impact Inventory
document: inventory/plugin-impact
version: 0.2.0
status: Draft
phase: 1
source_repository: https://github.com/ohcnetwork/care
source_branch: gcp
source_commit: 6a2976dc2512c2c532fcc70628c5690fbbbe3f3d
reviewed: 2026-08-07
---

# Plugin Impact Inventory

How CARE loads plugins, what is bundled at this commit, and what can and cannot
be determined about plugin compatibility from this repository alone.

Evidence labels: **verified** / **inferred** / **unknown**.

---

## 1. Headline

**verified** **No plugins are bundled at this commit.** `plug_config.py:4` is:

```python
plugs = []
```

**verified** Therefore `PLUGIN_APPS` is empty, no plugin app is installed, no
plugin URL is routed, and no plugin migration exists **in this configuration**.

**verified** However, plugins can be injected at build time or runtime **without
touching this repository**, via the `ADDITIONAL_PLUGS` environment variable. So
"no plugins bundled" is not the same as "no plugins in a given deployment".

---

## 2. Loading mechanism

**verified** Four files implement the whole system:

| File | Role |
| --- | --- |
| `plug_config.py` | Declares the plug list; instantiates `PlugManager` |
| `plugs/plug.py` | The `Plug` dataclass |
| `plugs/manager.py` | `PlugManager` — install, app list, config aggregation |
| `install_plugins.py` | Build-time entrypoint: `manager.install()` |

**verified** `plugs/plug.py:5-10` — the `Plug` dataclass:

```python
@dataclass(slots=True)
class Plug:
    name: str
    package_name: str
    version: str = field(default="@main")
    configs: dict = field(default_factory=dict)
```

**verified** `version` defaults to `"@main"` (`plug.py:8`) — a **git ref, not a
pinned release**. **inferred** the default installs a moving target; two builds
of the same commit can produce different plugin code.

### 2.1 Runtime injection

**verified** `plugs/manager.py:22-29`:

```python
if additional_plugs := os.getenv("ADDITIONAL_PLUGS"):
    try:
        for plug in json.loads(additional_plugs):
            self.add_plug(Plug(**plug))
    except json.JSONDecodeError:
        logger.error("ADDITIONAL_PLUGS is not a valid JSON")
```

**verified** `ADDITIONAL_PLUGS` is read from the environment when
`PlugManager.__init__` runs — which happens at
`config/settings/base.py:19` (`from plug_config import manager`), i.e. **at
Django settings import time, in every process**.

**verified** Malformed JSON is logged and swallowed (`manager.py:27-28`). The
process starts with **zero** plugins rather than failing. **inferred** a typo in
`ADDITIONAL_PLUGS` silently disables every plugin instead of crashing — a
deployment hazard on Cloud Run, where the symptom would be missing endpoints
rather than a failed rollout.

### 2.2 Installation

**verified** `plugs/manager.py:31-35`:

```python
def install(self) -> None:
    packages = {f"{x.package_name}{x.version}" for x in self.plugs}
    if packages:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])
```

**verified** This runs `pip install` in a subprocess. It is invoked from
`install_plugins.py` at **image build time**, `docker/prod.Dockerfile:39`:

```dockerfile
ARG ADDITIONAL_PLUGS=""
ENV ADDITIONAL_PLUGS=$ADDITIONAL_PLUGS
RUN python3 $APP_HOME/install_plugins.py
```

**verified** `ADDITIONAL_PLUGS` is plumbed through compose as a build arg:
`docker-compose.local.yaml:7-8`.

**verified critical asymmetry:** `ADDITIONAL_PLUGS` is consumed in **two
different phases**:

| Phase | Consumer | Effect |
| --- | --- | --- |
| Image build | `install_plugins.py` → `manager.install()` | `pip install`s the packages |
| Every process start | `config/settings/base.py:19` → `PlugManager.__init__` | Adds them to `INSTALLED_APPS` |

**inferred** If the runtime value differs from the build-time value, Django lists
an app in `INSTALLED_APPS` that was never pip-installed, and the process dies at
startup with `ModuleNotFoundError`. On Cloud Run — where the image and the env
vars are configured independently — this is an easy misconfiguration. The
variable must be identical at build and deploy.

### 2.3 Integration points

**verified** Exactly three:

| Integration | Location | Mechanism |
| --- | --- | --- |
| Apps | `config/settings/base.py:142, 149` | `PLUGIN_APPS = manager.get_apps()`; appended to `INSTALLED_APPS` |
| Settings | `config/settings/base.py:146` | `PLUGIN_CONFIGS = manager.get_config()` |
| URLs | `config/urls.py:111-112` | `path(f"api/{plug}/", include(f"{plug}.urls"))` |

**verified** `config/urls.py:111-112` requires every plugin to expose a
`urls` module. There is no `try`/`except` — a plugin without `urls.py` raises at
import and the process fails to start.

**verified** `manager.get_config()` (`manager.py:41-49`) returns a
`defaultdict[str, dict]` keyed by plugin name. **unknown** how plugins read it;
no consumer of `PLUGIN_CONFIGS` exists in this repository beyond its definition.

**verified** `PlugConfig` is also a **database model** with its own viewset
(`care/users/api/viewsets/plug_config.py`), distinct from `PLUGIN_CONFIGS`.
Its `list` action is **unauthenticated** — `get_authenticators` returns `[]` for
`GET` (`plug_config.py:36-39`) — and the response is cached under
`care_plug_viewset_list` (`plug_config.py:14, 17-22`).

---

## 3. Impact assessment per risk category

Because `plugs = []`, every row below is about what a plugin **could** introduce,
not what one does today.

| Risk | Determinable here? | Assessment |
| --- | --- | --- |
| Celery tasks | **no** | `app.autodiscover_tasks()` (`config/celery_app.py:18`) scans every app in `INSTALLED_APPS`. Any plugin `tasks.py` is registered automatically and would need a Cloud Tasks route. |
| Redis dependencies | **no** | A plugin can import `django_redis` or call `cache.set(..., nx=True)` freely. Nothing constrains it. |
| Direct S3 / boto3 | **no** | `boto3` is a core dependency, importable by any plugin. |
| Signed URLs | **partly, since ES-01** | CARE no longer generates any. `S3FilesManager` is still importable from `care.emr.utils.file_manager` but exposes no signed-URL method — see §9. A plugin can still construct its own `boto3` client, so the guarantee is CARE's, not the platform's. |
| Custom health checks | **partly** | `HEALTHY_DJANGO` (`config/settings/base.py:453-467`) is a plain list. A plugin cannot append to it through the plug system — no hook exists. **inferred** plugins cannot register health checks. |
| Custom startup behavior | **no** | Standard Django `AppConfig.ready()` is available to any plugin app. |
| Additional migrations | **no** | Plugin apps are ordinary Django apps; their migrations run with `migrate`. Given §2 of `runtime-and-deployment.md`, they would run only in the Celery Beat container. |

**verified** The health-check row is the only category the plug system
structurally prevents. All others are wide open because plugins are just Django
apps with unrestricted imports.

---

## 4. What cannot be determined

**unknown**, and not determinable from this repository:

1. **Which plugins any given deployment runs.** Governed by `ADDITIONAL_PLUGS`,
   set outside version control.
2. **Whether known CARE plugins are GCP-compatible.** No plugin source is vendored.
3. **Plugin Celery task shapes** — payloads, retries, idempotency.
4. **Plugin storage usage** — buckets, signed URLs, direct object access.
5. **Plugin Redis usage** — locks, raw clients, pattern deletes.
6. **Plugin migration dependencies** on core CARE tables.
7. **What `PLUGIN_CONFIGS` keys mean**, since no consumer exists here.

**verified** The repository offers no manifest, lockfile or compatibility matrix
for plugins. `plug_config.py` is the only declaration point and it is empty.

**inferred** Any statement that "CARE plugins work on GCP" is unsupportable from
this repository. Each deployment's plugin set has to be inventoried separately,
using the same method applied here to core CARE.

---

## 5. Consequences for the GCP migration

**inferred**, flowing from verified facts above:

1. **The plugin system is a hole in every other inventory in this directory.**
   The storage, task and cache inventories are complete for *core CARE at this
   commit*. They are not complete for any deployment with plugins.

2. **`autodiscover_tasks` means plugin tasks appear without registration**
   (`config/celery_app.py:18`). A Cloud Tasks design that enumerates known tasks
   by hand will silently drop them.

3. **`ADDITIONAL_PLUGS` must match between build and deploy** (§2.2), and a JSON
   typo disables plugins silently (§2.1). Both deserve a startup assertion.

4. **`version` defaults to `@main`** (`plugs/plug.py:8`). Reproducible GCP builds
   require explicit pins.

5. **Plugins cannot contribute health checks** (§3), so the Cloud Run health
   endpoint stays under core control.

6. **Plugin migrations inherit the beat-only migration problem**
   (`runtime-and-deployment.md` §2). Whatever replaces beat must run them too.

**Recommendation (inferred):** treat the plugin set as an explicit input to the
GCP design. Before deploying, run this same inventory against each plugin the
target deployment actually installs. Document that set in
`07-configuration-reference.md` rather than assuming the empty default.

---

## 9. Storage API change in ES-01 (deprecation notice)

Recorded 2026-08-07.

**verified** `care.emr.utils.file_manager.S3FilesManager` — the one storage
symbol this inventory identified as plugin-reachable — still imports and still
works. It is now a **deprecated** subclass of `FilesManager`.

What changed:

| Aspect | Before | After |
| --- | --- | --- |
| Base | own class over `boto3` | `FilesManager`, delegating to Django Storage |
| Constructor argument | `BucketType.PATIENT` | `"PATIENT"` or `"patient"`; the old enum member still works via its `.value` |
| `put_object` / `get_object` / `delete_object` | boto3 calls, returned provider response dicts | Django Storage; return a name, a file object, or `None` |
| `put_object(**kwargs)` | passed provider kwargs through | replaced by an optional `content_type` |
| `file_contents` | `(content_type, bytes)` tuple | `bytes` |
| `delete_object(quiet=...)` | argument accepted | removed; deletion is idempotent |
| `signed_url` / `read_signed_url` | present | **removed** |
| Unknown bucket argument | n/a | raises `ValueError` |

**Importing it emits a `DeprecationWarning`.** Migrate to
`FilesManager("patient")` or, better,
`django.core.files.storage.storages["patient"]`.

**The signed-URL removal is deliberate and will not be restored.** ADR-0001
requires that no storage-provider URL reach a client. A plugin that needs to
hand a file to a browser should link to the CARE download route rather than mint
a bucket URL:

```http
GET /api/v1/files/{external_id}/download/
```

**verified** Nothing prevents a plugin from importing `boto3` itself and
generating its own presigned URL — `boto3` remains a core dependency for SNS.
The guarantee ES-01 establishes is that *CARE* generates none; it is not
enforced against plugin code. **Recommend** adding this to plugin review
criteria rather than attempting to block the import.

**unknown** Which plugins, if any, import `S3FilesManager`. No plugin source is
vendored here, so the shim is retained on the assumption that some do.
