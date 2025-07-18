# Use Alpine-based Python image
FROM python:3.13-alpine AS base

ARG APP_HOME=/app
ARG TYPST_VERSION=0.12.0

ENV APP_HOME=${APP_HOME}
WORKDIR $APP_HOME

ENV PIPENV_CACHE_DIR=/root/.cache/pip
ENV PATH="/.venv/bin:$PATH"

# Install system dependencies
RUN apk add --no-cache \
    build-base \
    jpeg-dev \
    zlib-dev \
    gmp-dev \
    postgresql-dev \
    gettext \
    wget \
    curl \
    git \
    bash \
    gnupg \
    postgresql-libs \
    && python -m venv /.venv

# Install Pipenv
RUN --mount=type=cache,target=/root/.cache/pip pip install pipenv==2024.4.0

# Install typst
COPY --chmod=0755 scripts/install_typst.sh $APP_HOME
RUN TYPST_VERSION=${TYPST_VERSION} $APP_HOME/install_typst.sh

# Copy dependency files and install Python deps
COPY Pipfile Pipfile.lock $APP_HOME/
RUN --mount=type=cache,target=/root/.cache/pip \
    pipenv install --system --categories "packages dev-packages docs"

# Copy source code
COPY . $APP_HOME/

# Install plugins
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 $APP_HOME/install_plugins.py

# Add healthcheck
HEALTHCHECK \
  --interval=10s \
  --timeout=5s \
  --start-period=10s \
  --retries=48 \
  CMD ["./scripts/healthcheck.sh"]
