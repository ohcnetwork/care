ARG PYTHON_VERSION=3.11-slim-bullseye

FROM python:${PYTHON_VERSION} as base

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1


# ---
FROM base as builder

ARG BUILD_ENVIRONMENT=production

ENV PATH /venv/bin:$PATH

RUN apt-get update && apt-get install --no-install-recommends -y \
  build-essential libjpeg-dev zlib1g-dev libpq-dev git

# use pipenv to manage virtualenv
RUN python -m venv /venv
RUN pip install pipenv

COPY Pipfile Pipfile.lock ./
RUN pipenv sync --system --categories "packages"

COPY . /app

RUN python3 /app/install_plugins.py

# ---
FROM base as runtime

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=/app
ARG APP_VERSION="unknown"

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV BUILD_ENV ${BUILD_ENVIRONMENT}
ENV APP_VERSION ${APP_VERSION}

ENV PATH /venv/bin:$PATH

WORKDIR ${APP_HOME}

RUN apt-get update && apt-get install --no-install-recommends -y \
  libpq-dev gettext wget curl gnupg chromium \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# copy in Python environment
COPY --from=builder /venv /venv

COPY --chmod=0755 ./scripts/*.sh ./

HEALTHCHECK \
  --interval=30s \
  --timeout=5s \
  --start-period=10s \
  --retries=6 \
  CMD ["/app/healthcheck.sh"]

COPY . ${APP_HOME}

EXPOSE 9000
