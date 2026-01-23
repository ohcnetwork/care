job "care-postgres" {
  datacenters = ["dc1"]
  type        = "service"

  group "postgres" {
    count = 1

    network {
      port "db" {
        static = 5432
      }
    }

    task "postgres" {
      driver = "docker"

      config {
        image = "postgres:18-alpine"
        ports = ["db"]
      }

      env {
        POSTGRES_DB       = "care"
        POSTGRES_USER     = "postgres"
        POSTGRES_PASSWORD = "postgres"
      }

      resources {
        cpu    = 500
        memory = 1024
      }
    }
  }
}
