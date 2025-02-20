FROM python:3.13-slim-bookworm

ARG APP_HOME=/app
ARG TYPST_VERSION=0.12.0

WORKDIR $APP_HOME

ENV PIPENV_CACHE_DIR=/root/.cache/pip

RUN apt-get update && apt-get install --no-install-recommends -y \
  build-essential libjpeg-dev zlib1g-dev libgmp-dev \
  libpq-dev gettext wget curl gnupg git \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

COPY --chmod=0755 scripts/install_typst.sh $APP_HOME
RUN TYPST_VERSION=${TYPST_VERSION} $APP_HOME/install_typst.sh

# use pipenv to manage virtualenv
ENV PATH=/.venv/bin:$PATH
RUN python -m venv /.venv
RUN --mount=type=cache,target=/root/.cache/pip pip install pipenv==2024.4.0

COPY Pipfile Pipfile.lock $APP_HOME/
RUN --mount=type=cache,target=/root/.cache/pip pipenv  install --system --categories "packages dev-packages docs"

COPY . $APP_HOME/

RUN --mount=type=cache,target=/root/.cache/pip python3 $APP_HOME/install_plugins.py

HEALTHCHECK \
  --interval=10s \
  --timeout=5s \
  --start-period=10s \
  --retries=48 \
  CMD ["./scripts/healthcheck.sh"]
