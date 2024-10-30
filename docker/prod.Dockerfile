FROM python:3.13-slim-bookworm AS base

ARG APP_HOME=/app
ARG TYPST_VERSION=0.11.0

ARG BUILD_ENVIRONMENT="production"
ARG APP_VERSION="unknown"
ARG ADDITIONAL_PLUGS=""

ENV BUILD_ENVIRONMENT=$BUILD_ENVIRONMENT
ENV APP_VERSION=$APP_VERSION
ENV ADDITIONAL_PLUGS=$ADDITIONAL_PLUGS
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH=/venv/bin:$PATH

WORKDIR $APP_HOME

# ---
FROM base AS builder

RUN apt-get update && apt-get install --no-install-recommends -y \
  build-essential libjpeg-dev zlib1g-dev libgmp-dev libpq-dev git wget \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# Download and install Typst for the correct architecture
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        TYPST_ARCH="x86_64-unknown-linux-musl"; \
    elif [ "$ARCH" = "arm64" ]; then \
        TYPST_ARCH="aarch64-unknown-linux-musl"; \
    else \
        echo "Unsupported architecture: $ARCH"; \
        exit 1; \
    fi && \
    wget -qO typst.tar.xz https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-${TYPST_ARCH}.tar.xz && \
    tar -xf typst.tar.xz && \
    mv typst-${TYPST_ARCH}/typst /usr/local/bin/typst && \
    rm -rf typst.tar.xz typst-${TYPST_ARCH}

# use pipenv to manage virtualenv
RUN python -m venv /venv
RUN pip install pipenv==2024.2.0

COPY Pipfile Pipfile.lock $APP_HOME
RUN pipenv sync --system --categories "packages"

COPY plugs/ $APP_HOME/plugs/
COPY install_plugins.py plug_config.py $APP_HOME
RUN python3 $APP_HOME/install_plugins.py

# ---
FROM base AS runtime

RUN apt-get update && apt-get install --no-install-recommends -y \
  libpq-dev libgmp-dev gettext wget curl gnupg \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

COPY --from=builder --chmod=0755 /usr/local/bin/typst /usr/local/bin/typst

COPY --from=builder /venv /venv

COPY --chmod=0755 ./scripts/*.sh $APP_HOME

COPY . $APP_HOME

HEALTHCHECK \
  --interval=30s \
  --timeout=5s \
  --start-period=10s \
  --retries=12 \
  CMD ["/app/healthcheck.sh"]

EXPOSE 9000
