# Nomad Setup Guide

Nomad orchestrates the CARE application and its dependencies in a development environment.

## Quick Start

### Starting the Nomad Cluster

```bash
./scripts/nomad-up.sh
```

### Stopping the Nomad Cluster

```bash
./scripts/nomad-down.sh
```

### Check Status

```bash
make nomad-status
```

### Accessing the Application

- **Nomad UI**: http://localhost:4646
- **Backend API**: http://localhost:9000
