# Woodpecker CI Configuration

Woodpecker CI workflows for CARE backend.

## Workflows

### test.yml

**Triggers:** Pull requests, pushes to develop/staging

-   Builds dev Docker image with registry cache
-   Starts PostgreSQL 16, Redis 8 via docker-compose
-   Checks migrations, validates fixtures
-   Runs test suite with coverage
-   Uploads to Codecov
-   Dumps database for frontend tests

### deploy.yml

**Triggers:** Pushes to develop/staging, version tags, manual

-   Multi-platform builds (linux/amd64, linux/arm64)
-   Registry-based layer caching
-   Tags: production-latest, staging-latest, latest, semver
-   Pushes to ghcr.io
-   Creates Sentry release

### lint.yml

**Triggers:** Pull requests, merge queue

-   Runs pre-commit hooks on changed files
-   Shows diff on failure

### release.yml

**Triggers:** Pushes to production branch

-   Calendar versioning (YY.WW.MINOR)
-   Creates and pushes Git tag
-   Creates draft GitHub release with auto-generated notes

### docs.yml

**Triggers:** Pushes/PRs affecting docs/ directory

-   Builds Sphinx HTML documentation
-   Deploys to GitHub Pages (gh-pages branch)

## Required Secrets

| Secret Name         | Purpose                            | Used In                     |
| ------------------- | ---------------------------------- | --------------------------- |
| `registry_username` | GitHub username for GHCR           | test, deploy                |
| `github_token`      | GitHub PAT with `write:packages`   | test, deploy, docs, release |
| `codecov_token`     | Codecov upload token               | test                        |
| `sentry_auth_token` | Sentry release creation (optional) | deploy                      |
| `sentry_org`        | Sentry organization (optional)     | deploy                      |
| `sentry_project`    | Sentry project name (optional)     | deploy                      |

Configure via Woodpecker UI (Repository → Settings → Secrets) or CLI:

```bash
woodpecker-cli secret add --repository ohcnetwork/care --name github_token --value "ghp_..."
```

## Local Testing

```bash
docker compose -f docker-compose.woodpecker.yml up -d
# Access UI at http://localhost:8000

# Or use CLI
woodpecker-cli exec --local .woodpecker/test.yml
```
