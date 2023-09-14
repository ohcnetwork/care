FROM public.ecr.aws/lambda/python:3.11 as base


# ---
FROM base as builder

ARG BUILD_ENVIRONMENT=lambda

RUN yum update -y && \
    yum install -y \
    gcc python3-devel python3-pip \
    libjpeg-devel zlib-devel \
    amazon-linux-extras \
    gettext wget gnupg chromium \
    # use postgresql 14
    && PYTHON=python2 amazon-linux-extras enable postgresql14 \
    && yum install -y postgresql-devel

ENV PATH /usr/pgsql-14/bin:/usr/pgsql-14/lib:$PATH

RUN pip install --upgrade wheel pipenv
COPY Pipfile Pipfile.lock ./
RUN pipenv requirements --categories "packages" > requirements.txt

RUN pip wheel --wheel-dir /usr/src/app/wheels  \
  -r requirements.txt psycopg[binary]==3.1.*


# ---
FROM base as runtime

ARG BUILD_ENVIRONMENT=production
ARG APP_HOME=${LAMBDA_TASK_ROOT}

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV BUILD_ENV ${BUILD_ENVIRONMENT}

WORKDIR ${APP_HOME}

RUN yum update -y && yum install -y \
  amazon-linux-extras \
  gettext wget gnupg chromium \
  # use postgresql 14
  && PYTHON=python2 amazon-linux-extras enable postgresql14 \
  && yum install -y postgresql-devel \
  # cleanup
  && yum autoremove -y && rm -rf /var/cache/yum/*

ENV PATH /usr/pgsql-14/bin:/usr/pgsql-14/lib:$PATH

COPY --from=builder /usr/src/app/wheels  /wheels/
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
  && rm -rf /wheels/

COPY . ${APP_HOME}

RUN set -o allexport; source docker/.prebuilt.env; set +o allexport; \
  python manage.py collectstatic --noinput

CMD ["config.mangum_handler.handler"]
