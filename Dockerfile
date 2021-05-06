FROM vichuhari100/care-production-base:latest

RUN addgroup --system django \
  && adduser --system --ingroup django django

COPY ./start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start
RUN chown django /start

COPY --chown=django:django . /app

USER django

WORKDIR /app

EXPOSE 9000
