FROM python:3.7-slim-buster

ENV PYTHONUNBUFFERED 1

RUN apt-get update \
  # dependencies for building Python packages
  && apt-get install -y build-essential libgdal-dev python3-dev \
  # psycopg2 dependencies
  && apt-get install -y libpq-dev \
  # Translations dependencies
  && apt-get install -y gettext wget curl gnupg2 vim \
  # Html to PDF Converter Requirements
  # && apt-get install -y  chromium-browser \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# Install x11vnc.
# RUN apt-get install -y x11vnc
# Install xvfb.
# RUN apt-get install -y xvfb
# # Install fluxbox.
# RUN apt-get install -y fluxbox
# # Install wget.
# RUN apt-get install -y wget
# # Install wmctrl.
# RUN apt-get install -y wmctrl
# Set the Chrome repo.
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
  && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list
# Install Chrome.
RUN apt-get update && apt-get -y install google-chrome-stable

RUN addgroup --system django \
  && adduser --system --ingroup django django

# Requirements are installed here to ensure they will be cached.
COPY ./requirements /requirements
RUN pip install --no-cache-dir -r /requirements/production.txt \
  && rm -rf /requirements

COPY ./start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start
RUN chown django /start

COPY --chown=django:django . /app

# USER django

WORKDIR /app

EXPOSE 9000