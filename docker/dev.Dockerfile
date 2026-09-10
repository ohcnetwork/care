FROM python:3.14-slim-bookworm

ARG APP_HOME=/app

WORKDIR $APP_HOME

ENV PIPENV_CACHE_DIR=/root/.cache/pip

RUN apt-get update && apt-get install --no-install-recommends -y \
  build-essential libjpeg-dev zlib1g-dev libgmp-dev \
  libpq-dev libpangoft2-1.0-0 gettext wget curl gnupg git \
  libharfbuzz0b libharfbuzz-subset0 libffi-dev libjpeg-dev libopenjp2-7-dev \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# use pipenv to manage virtualenv
ENV PATH=/.venv/bin:$PATH
RUN python -m venv /.venv
RUN --mount=type=cache,target=/root/.cache/pip pip install pipenv==2025.1.1

COPY Pipfile Pipfile.lock $APP_HOME/
RUN --mount=type=cache,target=/root/.cache/pip pipenv  install --system --categories "packages dev-packages docs"

ARG ADDITIONAL_PLUGS=""
ENV ADDITIONAL_PLUGS=$ADDITIONAL_PLUGS

COPY . $APP_HOME/

RUN --mount=type=cache,target=/root/.cache/pip python3 $APP_HOME/install_plugins.py

HEALTHCHECK \
  --interval=10s \
  --timeout=5s \
  --start-period=10s \
  --retries=48 \
  CMD ["./scripts/healthcheck.sh"]
