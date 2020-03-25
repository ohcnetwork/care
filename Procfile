web: gunicorn config.wsgi:application
release: python manage.py collectstatic --noinput && python manage.py migrate
