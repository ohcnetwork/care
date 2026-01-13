# Nix Development Environment for CARE

This document describes how to set up and use the Nix-based development environment for the CARE project.

## Prerequisites

1. **Install Nix**: Follow the installation instructions at [nixos.org](https://nixos.org/download.html) or use the Determinate Systems installer:
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
   ```

   > **Note**: The Determinate Systems installer is preferred as it provides a cleaner installation process and hassle-free uninstallation from user machines.

2. **Enable Flakes**: Nix flakes should be enabled automatically with modern installers. If not, add to `~/.config/nix/nix.conf`:
   ```
   experimental-features = nix-command flakes
   ```

3. **Optional - Install direnv**: For automatic environment activation:
   ```bash
   # On macOS with Homebrew
   brew install direnv

   # On Linux (varies by distribution)
   sudo apt install direnv  # Ubuntu/Debian
   sudo dnf install direnv  # Fedora
   ```

## Automated Setup

For first-time setup, use the automated setup script:

```bash
./scripts/nix-dev-setup.sh
```

This script will:
- Check if Nix is installed and flakes are enabled
- Set up the Python virtual environment and install dependencies
- Start required services (PostgreSQL, Redis, MinIO)
- Run database migrations
- Optionally load sample fixtures
- Provide helpful guidance for next steps

The script includes safety checks and won't run on NixOS systems (which should use NixOS-specific configurations).

## Quick Setup (Manual)

For first-time setup without the script:

```bash
nix develop
setup-dev
start-services
rundev
```

This will:
- Enter the development environment
- Set up Python virtual environment and install dependencies
- Start required services (PostgreSQL, Redis, MinIO)
- Run database migrations and start the unified development server

## Manual Setup

If you prefer manual setup or need to troubleshoot:

### 1. Enter Development Shell

```bash
nix develop
```

This will:
- Install all required system packages from Nix store
- Set up environment variables
- Make development commands available
- Show a helpful welcome message

### 2. Install Python Dependencies

```bash
setup-dev
```

### 3. Start Services

```bash
start-services
```

This starts:
- PostgreSQL on port 5432
- Redis on port 6379
- MinIO on port 9100 (console on 9001)

### 4. Set Up Database

```bash
migrate
load-fixtures  # Optional: load sample data
```

### 5. Start Complete Development Environment

#### Option A: Unified Start (Recommended)
```bash
rundev
```

This single command starts both the Django server and Celery worker together with proper migrations and setup.

#### Option B: Separate Services
```bash
# Terminal 1: Django server
runserver

# Terminal 2: Celery worker
celery
```

The Django server will be available at http://localhost:9000

## Available Commands

Once in the development shell (`nix develop`), you have access to these commands:

### Service Management
- `start-services` - Start PostgreSQL, Redis, and MinIO
- `stop-services` - Stop background services only
- `kill-care` - **🛑 Stop ALL development processes and services**
- `clean-data` - **🗑️ Remove all local service data** (requires confirmation)
- `healthcheck` - Check application health

### Development Server
- `rundev` - **🚀 Start both API server and Celery worker (RECOMMENDED)**
- `runserver` - Start Django development server only
- `celery` - Start Celery worker with beat scheduler only

### Database Operations
- `migrate` - Run database migrations
- `makemigrations [app]` - Create new migrations
- `load-fixtures` - Load sample data
- `dump-db` - Backup database to `care_db.dump`
- `load-db` - Restore database from `care_db.dump`
- `reset-db` - Drop and recreate database

### Django Management
- `manage <command>` - Run any Django management command
- `manage shell` - Django shell
- `manage collectstatic` - Collect static files

### Testing
- `test [path]` - Run tests (with database reuse)
- `test-no-keep [path]` - Run tests (fresh database)
- `test-coverage` - Run tests with coverage report

### Code Quality
- `ruff` - Check and fix staged files
- `ruff-all` - Check all Python files
- `ruff-fix-all` - Fix all Python files

### Initial Setup
- `setup-dev` - Install dependencies and set up environment

## Environment Variables

The development environment sets these variables automatically:

### Database
- `POSTGRES_USER=postgres`
- `POSTGRES_PASSWORD=postgres`
- `POSTGRES_HOST=localhost`
- `POSTGRES_DB=care`
- `POSTGRES_PORT=5432`
- `DATABASE_URL=postgres://postgres:postgres@localhost:5432/care`

### Redis
- `REDIS_URL=redis://localhost:6379`
- `CELERY_BROKER_URL=redis://localhost:6379/0`

### Django
- `DJANGO_DEBUG=true`
- `ATTACH_DEBUGGER=false`
- `DJANGO_SETTINGS_MODULE=config.settings.local`

### MinIO/S3
- `BUCKET_REGION=ap-south-1`
- `BUCKET_KEY=minioadmin`
- `BUCKET_SECRET=minioadmin`
- `BUCKET_ENDPOINT=http://localhost:9100`
- `BUCKET_EXTERNAL_ENDPOINT=http://localhost:9100`
- `FILE_UPLOAD_BUCKET=patient-bucket`
- `FACILITY_S3_BUCKET=facility-bucket`

## Service URLs

- **Django Application**: http://localhost:9000
- **MinIO Console**: http://localhost:9001 (admin: minioadmin/minioadmin)
- **PostgreSQL**: localhost:5432 (postgres/postgres)
- **Redis**: localhost:6379

## Development Workflow

### Daily Development

#### Quick Start (Recommended)

1. **Start your session**:
   ```bash
   nix develop
   start-services  # If not already running
   ```

2. **Start the complete application**:
   ```bash
   rundev  # Starts both Django server and Celery worker together
   ```

#### Manual Start (Advanced)

1. **Start your session**:
   ```bash
   nix develop
   start-services  # If not already running
   ```

2. **Start services separately**:
   ```bash
   # Terminal 1: Django server
   runserver

   # Terminal 2: Celery worker
   celery
   ```

3. **Make changes and test**:
   ```bash
   ruff-all          # Check code style
   test              # Run tests
   manage shell      # Interactive Django shell
   ```

4. **Stop when done**:
   ```bash
   kill-care         # Stop all development processes
   ```

### Working with Database

```bash
# Create and apply migrations
makemigrations
migrate

# Reset database if needed
stop-services
reset-db
start-services
migrate
load-fixtures
```

### Debugging

#### Enable Django Debug Mode
Set `ATTACH_DEBUGGER=true` and use `runserver` to start with debugpy on port 9876.

#### Check Services
```bash
# Check if services are running
ps aux | grep -E 'postgres|redis|minio'

# View service logs (if using systemd)
journalctl --user -f
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
pg_ctl status -D .nix-data/postgres

# Restart PostgreSQL
stop-services
start-services
```

## Troubleshooting

### Common Issues

1. **"Permission denied" errors**:
   ```bash
   # Ensure directories are writable
   mkdir -p .nix-data/postgres .nix-data/redis .nix-data/minio
   ```

2. **Services won't start**:
   ```bash
   # Stop any conflicting processes
   stop-services
   # Check for processes using ports
   lsof -i :5432  # PostgreSQL
   lsof -i :6379  # Redis
   lsof -i :9100  # MinIO
   ```

3. **Python dependencies issues**:
   ```bash
   # Stop everything first
   kill-care
   # Reinstall in clean environment
   rm -rf .venv
   setup-dev
   ```

4. **Database connection refused**:
   ```bash
   # Wait for PostgreSQL to fully start
   sleep 5
   # Or check if initialization is complete
   pg_ctl status -D .nix-data/postgres
   ```

### Clean Reset

If you encounter persistent issues:

```bash
# Stop all processes and services
kill-care

# Clean up data directories (will prompt for confirmation)
clean-data

# Exit and re-enter development shell
exit
nix develop

# Restart setup
setup-dev
start-services
migrate
```

## Data Storage

The Nix development environment stores all service data in the project-local `.nix-data` directory:

- **PostgreSQL data**: `.nix-data/postgres/`
- **Redis data**: `.nix-data/redis/`
- **MinIO data**: `.nix-data/minio/`

This directory is automatically added to `.gitignore` and provides isolation from system-wide services.

## Differences from Docker Setup

### Advantages of Nix
- **Faster startup**: No container overhead
- **Native performance**: Direct system execution
- **Reproducible**: Same environment across different machines
- **Integrated tooling**: All tools available in single shell
- **Easier debugging**: Direct access to processes and files
- **Version pinning**: All tools use specific versions from Nix store

### Key Differences
- Services run directly on host (not in containers)
- Data stored in `.nix-data/` instead of Docker volumes
- Environment variables set in shell instead of env files
- All commands available directly (no `docker compose exec`)
- Uses Python 3.13 and PostgreSQL 15 from Nix store

## Integration with Existing Workflow

The Nix setup coexists with Docker setup:
- Makefile commands still work when using Docker
- Same Python dependencies and versions
- Same database schema and migrations
- Compatible with existing CI/CD pipelines

## Available Tools

The development environment includes these tools from the Nix store:

- **Python 3.13**: Base Python interpreter
- **PostgreSQL 15**: Database server and client tools
- **Redis**: In-memory data structure store
- **MinIO**: S3-compatible object storage
- **Pre-commit**: Git hook framework
- **GCC & build tools**: For compiling Python packages

## Contributing

When adding new dependencies:

1. **Python packages**: Add to `Pipfile` and run `setup-dev`
2. **System packages**: Add to `flake.nix` buildInputs
3. **Services**: Update service management scripts in `flake.nix`
4. **Environment variables**: Add to envVars in `flake.nix`

## Performance Tips

1. **Use direnv**: Automatically enter/exit development shell:
   ```bash
   echo "use flake" > .envrc
   direnv allow
   ```

2. **Keep services running**: Services persist between shell sessions

3. **Use test database reuse**: Default `test` command reuses database for speed

4. **Parallel testing**: Tests run in parallel by default

5. **Clean shutdown**: Use `kill-care` command to properly stop all processes

## Security Notes

- Services bind to localhost only (not accessible externally)
- Default credentials are for development only
- MinIO uses development keys (minioadmin/minioadmin)
- Database has no password (local development only)
