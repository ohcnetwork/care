ARG PYTHON_VERSION=3.11-slim-bullseye

FROM python:${PYTHON_VERSION} as base

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1


# ---
FROM base as builder

ARG BUILD_ENVIRONMENT=production
ARG TYPST_VERSION=0.11.0

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
    wget -O typst.tar.xz https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-${TYPST_ARCH}.tar.xz && \
    tar -xf typst.tar.xz && \
    mv typst-${TYPST_ARCH}/typst /usr/local/bin/typst && \
    chmod +x /usr/local/bin/typst && \
    rm -rf typst.tar.xz typst-${TYPST_ARCH}

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
  libpq-dev gettext wget curl gnupg \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# copy in Python environment
COPY --from=builder /venv /venv

# copy typst binary from builder stage
COPY --from=builder /usr/local/bin/typst /usr/local/bin/typst

COPY --chmod=0755 ./scripts/*.sh ./

HEALTHCHECK \
  --interval=30s \
  --timeout=5s \
  --start-period=10s \
  --retries=12 \
  CMD ["/app/healthcheck.sh"]

COPY . ${APP_HOME}

EXPOSE 9000
