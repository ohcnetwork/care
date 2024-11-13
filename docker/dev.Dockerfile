FROM python:3.13-slim-bookworm

ARG TYPST_VERSION=0.11.0

ENV PATH=/venv/bin:$PATH

RUN apt-get update && apt-get install --no-install-recommends -y \
  build-essential libjpeg-dev zlib1g-dev libgmp-dev \
  libpq-dev gettext wget curl gnupg git \
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
    chmod +x /usr/local/bin/typst && \
    rm -rf typst.tar.xz typst-${TYPST_ARCH}

# use pipenv to manage virtualenv
RUN python -m venv /venv
RUN pip install pipenv==2024.2.0

COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --categories "packages dev-packages"

COPY . /app

RUN python3 /app/install_plugins.py

HEALTHCHECK \
  --interval=10s \
  --timeout=5s \
  --start-period=10s \
  --retries=48 \
  CMD ["/app/scripts/healthcheck.sh"]

WORKDIR /app
