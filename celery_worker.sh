export NEW_RELIC_CONFIG_FILE=/etc/newrelic.ini
newrelic-admin run-program celery --app=config.celery_app --loglevel=info worker