FROM python:3.13-slim-bookworm AS base

ARG APP_HOME=/app
ARG TYPST_VERSION=0.12.0

ARG BUILD_ENVIRONMENT="production"

WORKDIR $APP_HOME

ENV BUILD_ENVIRONMENT=$BUILD_ENVIRONMENT
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIPENV_VENV_IN_PROJECT=1
ENV PIPENV_CACHE_DIR=/root/.cache/pip
ENV PATH=$APP_HOME/.venv/bin:$PATH


# ---
FROM base AS builder

RUN apt-get update && apt-get install --no-install-recommends -y \
  build-essential libjpeg-dev zlib1g-dev libgmp-dev libpq-dev git wget \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

COPY --chmod=0755 scripts/install_typst.sh $APP_HOME
RUN TYPST_VERSION=${TYPST_VERSION} $APP_HOME/install_typst.sh

# use pipenv to manage virtualenv
RUN pip install pipenv==2024.4.0

RUN python -m venv $APP_HOME/.venv
COPY Pipfile Pipfile.lock $APP_HOME/
RUN pipenv install --deploy --categories "packages"

ARG ADDITIONAL_PLUGS=""
ENV ADDITIONAL_PLUGS=$ADDITIONAL_PLUGS

COPY plugs/ $APP_HOME/plugs/
COPY install_plugins.py plug_config.py $APP_HOME/
RUN python3 $APP_HOME/install_plugins.py

# ---
FROM base AS runtime

RUN addgroup --system django \
  && adduser --system --ingroup django django

RUN apt-get update && apt-get install --no-install-recommends -y \
  libpq-dev libgmp-dev gettext wget curl gnupg \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

RUN chown django:django $APP_HOME

COPY --from=builder --chmod=0755 /usr/local/bin/typst /usr/local/bin/typst

COPY --from=builder --chown=django:django $APP_HOME/.venv $APP_HOME/.venv

ARG APP_VERSION="unknown"
ENV APP_VERSION=$APP_VERSION

COPY --chmod=0755 --chown=django:django ./scripts/*.sh $APP_HOME

COPY --chown=django:django . $APP_HOME

USER django

HEALTHCHECK \
  --interval=30s \
  --timeout=5s \
  --start-period=10s \
  --retries=12 \
  CMD ["./healthcheck.sh"]

EXPOSE 9000
