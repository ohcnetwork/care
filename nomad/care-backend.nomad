job "care-backend" {
  datacenters = ["dc1"]
  type        = "service"

  group "backend" {
    count = 1

    network {
      port "http" {
        static = 9000
        to     = 9000
      }
    }


    task "api" {
      driver = "docker"

      config {
        image = "ghcr.io/ohcnetwork/care:latest"
        
        network_mode = "host"
        
        command = "/bin/sh"
        args = ["-c", <<EOF
echo "api" > /tmp/container-role

echo "Waiting for Database at localhost:5432..."
while ! /app/.venv/bin/python -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('127.0.0.1', 5432))" 2>/dev/null; do
  echo "... DB not ready yet"
  sleep 2
done
echo "Database is ready!"

echo "Waiting for Redis at localhost:6379..."
while ! /app/.venv/bin/python -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('127.0.0.1', 6379))" 2>/dev/null; do
  echo "... Redis not ready yet"
  sleep 2
done
echo "Redis is ready!"

echo "Running Migrations..."
/app/.venv/bin/python manage.py migrate --noinput

echo "Collecting Static Files..."
/app/.venv/bin/python manage.py collectstatic --noinput --clear

echo "Starting Gunicorn..."
/app/.venv/bin/python -m gunicorn config.wsgi:application --bind=0.0.0.0:9000 --workers=1 --timeout=120 --log-level=info --access-logfile=- --error-logfile=-
EOF
        ]
      }


      env {
        # Production Settings
        DJANGO_SETTINGS_MODULE = "config.settings.production"
        
        # Static Files Fix
        DJANGO_STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
        WHITENOISE_USE_FINDERS     = "True"

        # Security Overrides
        ALLOWED_HOSTS = "*"
        DEBUG         = "true"
        SECRET_KEY    = "insecure-dev-key"
        SECURE_SSL_REDIRECT          = "false"
        DJANGO_SECURE_SSL_REDIRECT   = "false"
        SESSION_COOKIE_SECURE        = "false"
        CSRF_COOKIE_SECURE           = "false"
        SECURE_HSTS_SECONDS          = "0"
        ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"

        # Storage
        USE_S3      = "false"
        STATIC_URL  = "/static/"
        STATIC_ROOT = "/app/staticfiles"
        MEDIA_URL   = "/media/"
        MEDIA_ROOT  = "/app/media"
        
        # CORS
        CORS_ALLOW_ALL_ORIGINS = "true"
        SECURE_HSTS_INCLUDE_SUBDOMAINS = "false"
        SECURE_HSTS_PRELOAD = "false"


        DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:5432/care"
        REDIS_URL    = "redis://127.0.0.1:6379/0"
      }

      resources {
        cpu    = 800
        memory = 1024
      }
    }
  }
}
