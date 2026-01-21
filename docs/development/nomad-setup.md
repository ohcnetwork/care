# Nomad Setup Guide

Nomad is used to orchestrate the Care application and its dependencies in a development environment. This guide explains how to set up and manage the Nomad cluster.

## Prerequisites

- Nomad installed and available in your PATH (`nomad` command)
- Docker installed and running
- At least 2GB of available RAM on your system

## Quick Start

### Starting the Nomad Cluster

To start all services (Nomad agent, PostgreSQL, Redis, and the Care backend), use either the script or Make command:

**Using Make (one-click):**

```bash
make nomad-up
```

**Or using the script directly:**

```bash
./scripts/nomad-up.sh
```

This will:

1. Start the Nomad development agent
2. Deploy PostgreSQL database
3. Deploy Redis cache
4. The Care backend can be deployed separately

### Stopping the Nomad Cluster

To stop all services:

**Using Make:**

```bash
make nomad-down
```

**Or using the script directly:**

```bash
./scripts/nomad-down.sh
```

This will:

1. Stop the Care backend job
2. Stop the Redis job
3. Stop the PostgreSQL job
4. Terminate the Nomad agent

### Checking Nomad Status

To check the status of all jobs:

```bash
make nomad-status
```

Or:

```bash
nomad job status
```

## Architecture

The Nomad setup consists of four main jobs:

### 1. **PostgreSQL Database** (`postgres.nomad`)

- **Type**: Service job
- **Port**: 5432
- **Image**: `postgres:15`
- **Resources**: 500 CPU, 1024 MB RAM
- **Configuration**:
    - Database: `care`
    - User: `postgres`
    - Password: `postgres`

The database stores all persistent application data.

### 2. **Redis Cache** (`redis.nomad`)

- **Type**: Service job
- **Port**: 6379
- **Image**: `redis:7`
- **Resources**: 200 CPU, 256 MB RAM

Redis is used for caching and message brokering for Celery task queue.

### 3. **Care Backend API** (`care-backend.nomad`)

- **Type**: Service job
- **Port**: 9000
- **Image**: `ghcr.io/ohcnetwork/care:latest`
- **Resources**: 800 CPU, 1024 MB RAM
- **Dependencies**: PostgreSQL, Redis

The backend runs the Django application with Gunicorn. On startup, it:

1. Waits for PostgreSQL to be ready
2. Waits for Redis to be ready
3. Runs database migrations
4. Collects static files
5. Starts the Gunicorn server on port 9000

**Environment Variables**:

- `DJANGO_SETTINGS_MODULE`: `config.settings.production`
- `DATABASE_URL`: `postgresql://postgres:postgres@127.0.0.1:5432/care`
- `REDIS_URL`: `redis://127.0.0.1:6379/0`
- Security settings (SSL, CSRF, HSTS) are relaxed for development
- `ALLOWED_HOSTS` and `CORS_ALLOW_ALL_ORIGINS` are set to `*` for development

### 4. **Load Fixtures** (`load-fixtures.nomad`)

- **Type**: Batch job
- **Image**: `ghcr.io/ohcnetwork/care:latest`
- **Resources**: 500 CPU, 512 MB RAM
- **Purpose**: Loads initial data into the database

This job runs the `manage.py load_fixtures` command to populate the database with initial data. It's configured to fail on exit (not retry).

## Managing Jobs

### Deploy a specific job

```bash
nomad job run nomad/postgres.nomad
nomad job run nomad/redis.nomad
nomad job run nomad/care-backend.nomad
nomad job run nomad/load-fixtures.nomad
```

### Check job status

```bash
# View all jobs
nomad job status

# View a specific job
nomad job status care-backend

# View allocations for a job
nomad job allocations care-backend
```

### View job logs

```bash
# List allocations
nomad job allocations care-backend

# View logs from an allocation
nomad alloc logs <allocation-id> api
```

### Stop a job

```bash
nomad job stop care-backend
```

### Stop and remove a job

```bash
nomad job stop -purge care-backend
```

## Nomad Web UI

Nomad provides a web-based dashboard:

- **URL**: `http://localhost:4646`
- **Access**: View job status, allocations, logs, and cluster information
- **Available after**: `make nomad-up` or `./scripts/nomad-up.sh` is executed

## Common Tasks

### Accessing the Database

```bash
# Connect to PostgreSQL running in Nomad
psql -h localhost -U postgres -d care -W
# Password: postgres
```

### Accessing Redis

```bash
# Connect to Redis running in Nomad
redis-cli -h localhost
```

### Accessing the API

Once the Care backend is running:

```bash
curl http://localhost:9000/api/v1/health/
```

### Viewing Backend Logs

```bash
# Get the allocation ID
nomad job allocations care-backend

# View logs (replace <allocation-id> with actual ID)
nomad alloc logs <allocation-id> api
```

### Restarting a Service

```bash
# Stop the job
nomad job stop care-backend

# Deploy it again
nomad job run nomad/care-backend.nomad
```

### Loading Fixture Data

After the backend is running, you can load fixture data:

**Using Make (one-click):**

```bash
make nomad-load-fixtures
```

**Or manually:**

```bash
nomad job run nomad/load-fixtures.nomad

# Check the status
nomad job status care-load-fixtures

# View logs
nomad alloc logs <allocation-id> load-fixtures
```

## Troubleshooting

### Nomad won't start

**Error**: "Nomad failed to start"

**Solution**:

- Check if port 4646 is already in use: `lsof -i :4646`
- Kill any existing Nomad process: `pkill nomad`
- Check `nomad.log` for detailed errors

### Services not communicating

**Error**: "Database is not ready" or "Redis not ready"

**Solution**:

- Ensure Docker is running: `docker ps`
- Check resource availability on your system
- Restart all services: `./scripts/nomad-down.sh` then `./scripts/nomad-up.sh`

### Backend failed to start

**Error**: Backend container exits immediately

**Solution**:

- Check backend logs: `nomad alloc logs <allocation-id> api`
- Verify PostgreSQL and Redis are running: `nomad job status`
- Check environment variables in `care-backend.nomad`

### Port conflicts

**Error**: "Port already in use"

**Solution**:

- Find what's using the port: `lsof -i :<port-number>`
- Stop the conflicting service or change the port in the Nomad job file
- Restart Nomad: `./scripts/nomad-down.sh && ./scripts/nomad-up.sh`

### Out of memory

**Error**: "OOM Killed" or memory allocation failures

**Solution**:

- Reduce resource allocations in the Nomad job files (adjust `memory` and `cpu` values)
- Close other applications to free up system resources
- Check available memory: `free -h`

## Development vs Production

This Nomad setup is configured for **development only** and should NOT be used in production:

- SSL/HTTPS is disabled
- `DEBUG = true`
- `ALLOWED_HOSTS = "*"`
- Weak `SECRET_KEY`
- CORS allows all origins
- Database credentials are hardcoded
- Single-container deployments (no redundancy)

For production deployments, use proper configuration management, secrets, scaling policies, and security settings.

## Additional Resources

- [Nomad Documentation](https://www.nomadproject.io/docs)
- [Docker Integration](https://www.nomadproject.io/docs/drivers/docker)
- [Django Settings](../../config/settings/production.py)
