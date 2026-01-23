job "care-backend" {
  datacenters = ["dc1"]
  type        = "service"

  group "backend" {
    count = 1

    network {
      port "http" {
        static = 9000
      }
    }

    task "api" {
      driver = "docker"

      config {
        image       = "ghcr.io/ohcnetwork/care:production-latest"
        ports       = ["http"]
        extra_hosts = ["host.docker.internal:host-gateway"]

        command = "bash"
        args = ["-c", <<EOF
python manage.py migrate --noinput
bash start.sh
EOF
        ]
      }

      env {
        # Django configuration
        DJANGO_SETTINGS_MODULE = "config.settings.production"

        # Database & cache
        DATABASE_URL      = "postgresql://postgres:postgres@host.docker.internal:5432/care"
        REDIS_URL         = "redis://host.docker.internal:6379/0"
        CELERY_BROKER_URL = "redis://host.docker.internal:6379/0"

        # PostgreSQL connection
        POSTGRES_HOST     = "host.docker.internal"
        POSTGRES_PORT     = "5432"
        POSTGRES_USER     = "postgres"
        POSTGRES_PASSWORD = "postgres"
        POSTGRES_DB       = "care"

        # Security settings
        DJANGO_ALLOWED_HOSTS                  = "[\"*\"]"
        DJANGO_SECURE_SSL_REDIRECT            = "False"
        DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS = "False"
        DJANGO_SECURE_HSTS_PRELOAD            = "False"
        DJANGO_SECURE_CONTENT_TYPE_NOSNIFF    = "False"
      }

      resources {
        cpu    = 800
        memory = 1024
      }
    }
  }
}
