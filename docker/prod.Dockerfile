FROM python:3.13-alpine AS base

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

# Install shared runtime dependencies
RUN apk add --no-cache \
  libpq gmp gettext curl wget su-exec

# ----------------
FROM base AS builder

# Install build tools and Python headers
RUN apk add --no-cache \
  build-base libjpeg-turbo-dev zlib-dev postgresql-libs gmp-dev postgresql-dev git

# Install Typst
COPY --chmod=0755 scripts/install_typst.sh $APP_HOME
RUN TYPST_VERSION=${TYPST_VERSION} $APP_HOME/install_typst.sh

# Install pipenv and dependencies
RUN python -m venv $APP_HOME/.venv \
+  && $APP_HOME/.venv/bin/pip install pipenv==2024.4.0 \
COPY Pipfile Pipfile.lock $APP_HOME/
RUN $APP_HOME/.venv/bin/pip install --upgrade "setuptools>=78.1.1"
RUN $APP_HOME/.venv/bin/pipenv install --deploy --system

# Plugin support
ARG ADDITIONAL_PLUGS=""
ENV ADDITIONAL_PLUGS=$ADDITIONAL_PLUGS

COPY plugs/ $APP_HOME/plugs/
COPY install_plugins.py plug_config.py $APP_HOME/
RUN python3 $APP_HOME/install_plugins.py

# ----------------
FROM base AS runtime

RUN addgroup -S django && adduser -S -G django django

# Copy Typst binary
COPY --from=builder --chmod=0755 /usr/local/bin/typst /usr/local/bin/typst

# Copy virtualenv
COPY --from=builder --chown=django:django $APP_HOME/.venv $APP_HOME/.venv

ARG APP_VERSION="unknown"
ENV APP_VERSION=$APP_VERSION

# Copy app scripts and source
COPY --chmod=0755 --chown=django:django ./scripts/*.sh $APP_HOME
COPY --chown=django:django . $APP_HOME

USER django

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=12 \
  CMD ["./healthcheck.sh"]

EXPOSE 9000
