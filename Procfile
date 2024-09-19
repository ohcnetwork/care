web: gunicorn config.wsgi:application
release: python manage.py collectstatic --noinput && python manage.py migrate
# Configuration with only one worker
worker: celery --app=config.celery_app worker -B --max-tasks-per-child=6 --loglevel=info
# Configuration with multiple workers
# worker: celery --app=config.celery_app worker --max-tasks-per-child=6 --loglevel=info
# beat: celery --app=config.celery_app beat --loglevel=info
