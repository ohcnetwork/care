watchmedo auto-restart --directory=./ --pattern='*.py' --recursive -- celery --app=config.celery_app worker  --concurrency=1 --loglevel=INFO
