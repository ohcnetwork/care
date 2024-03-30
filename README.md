# Care Backend

<p align="center">
  <a href="https://ohc.network">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="./care/static/images/logos/light-logo.svg">
      <img alt="care logo" src="./care/static/images/logos/black-logo.svg"  width="300">
    </picture>
  </a>
</p>

[![Deploy Care](https://github.com/coronasafe/care/actions/workflows/deployment.yaml/badge.svg)](https://github.com/coronasafe/care/actions/workflows/deployment.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg)](https://github.com/pydanny/cookiecutter-django/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Chat](https://img.shields.io/badge/-Join%20us%20on%20slack-7b1c7d?logo=slack)](https://slack.coronasafe.in/)

This is the backend for care. an open source platform for managing patients, health workers, and hospitals.

## Features

Care backend makes the following features possible:

- Realtime Analytics of Beds, ICUs, Ventilators, Oxygen and other resources in hospitals
- Facility Management with Inventory Monitoring
- Integrated Tele-medicine & Triage
- Patient Management and Consultation History
- Realtime video feed and vitals monitoring of patients
- Clinical Data Visualizations.

## Getting Started

### Docs and Guides

You can find the docs at https://care-be-docs.coronasafe.network

### Staging Deployments

Dev and staging instances for testing are automatically deployed on every commit to the `develop` and `staging` branches.
The staging instances are available at:

- https://careapi.ohc.network
- https://careapi-staging.ohc.network

### Self hosting

#### Compose

docker compose is the easiest way to get started with care.
put the required environment variables in a `.env` file and run:

```bash
make up
```

to load dummy data for testing run:

```bash
make load-dummy-data
```

> [!NOTE]
> If you are unable to compose up care in windows, ensure line endings are set to `LF` (`docker-entrypoint.sh` won't
> work with `CRLF` line endings).
> ```
> git config core.autocrlf false
> ```

#### Docker

Prebuilt docker images for server deployments are available
on [ghcr](https://github.com/coronasafe/care/pkgs/container/care)

## Contributing

We welcome contributions from everyone. Please read our [contributing guidelines](./CONTRIBUTING.md) to get started.
