job "care-load-fixtures" {
  datacenters = ["dc1"]
  type        = "batch"

  group "fixtures" {
    count = 1

    restart {
      attempts = 1
      interval = "10m"
      mode     = "fail"
    }

    task "load-fixtures" {
      driver = "docker"

      config {
        image = "ghcr.io/ohcnetwork/care:latest"

        entrypoint = ["/app/.venv/bin/python"]
        args = [
          "manage.py",
          "load_fixtures"
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
        cpu    = 500
        memory = 512
      }
    }
  }
}
