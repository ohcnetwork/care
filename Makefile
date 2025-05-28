.PHONY: logs


DOCKER_VERSION := $(shell docker --version 2>/dev/null)

docker_config_file := 'docker-compose.local.yaml'

all:
ifndef DOCKER_VERSION
    $(error "command docker is not available, please install Docker")
endif

install:
	pipenv install --categories "packages dev-packeges docs"

re-build:
	docker compose -f docker-compose.yaml -f $(docker_config_file) build --no-cache

build:
	docker compose -f docker-compose.yaml -f $(docker_config_file) build

pull:
	docker compose -f docker-compose.yaml -f $(docker_config_file) pull

up:
	docker compose -f docker-compose.yaml -f $(docker_config_file) up -d --wait

build-up-live:
	docker compose -f docker-compose.yaml -f $(docker_config_file) up --build

down:
	docker compose -f docker-compose.yaml -f $(docker_config_file) down

teardown:
	docker compose -f docker-compose.yaml -f $(docker_config_file) down -v

load-dummy-data:
	docker compose exec backend bash -c "python manage.py load_dummy_data"

load-fixtures:
	docker compose exec backend bash -c "python manage.py load_fixtures"

list:
	docker compose -f docker-compose.yaml -f $(docker_config_file) ps

logs:
	docker compose -f docker-compose.yaml -f $(docker_config_file) logs

checkmigration:
	docker compose exec backend bash -c "python manage.py makemigrations --check --dry-run"

makemigrations:
	docker compose exec backend bash -c "python manage.py makemigrations"

migrate:
	docker compose exec backend bash -c "python manage.py migrate"

test:
	docker compose exec backend bash -c "python manage.py test $(path) --keepdb --parallel --shuffle"

test-no-keep:
	docker compose exec backend bash -c "python manage.py test $(path) --parallel --shuffle"


test-coverage:
	docker compose exec backend bash -c "coverage run manage.py test --settings=config.settings.test --keepdb --parallel --shuffle"
	docker compose exec backend bash -c "coverage combine || true; coverage xml"
	docker compose cp backend:/app/coverage.xml coverage.xml

dump-db:
	docker compose exec db sh -c "pg_dump -U postgres -Fc care > /tmp/care_db.dump"
	docker compose cp db:/tmp/care_db.dump care_db.dump

load-db:
	docker compose cp care_db.dump db:/tmp/care_db.dump
	docker compose exec db sh -c "pg_restore -U postgres --clean --if-exists -d care /tmp/care_db.dump"

reset-db:
	docker compose exec db sh -c "dropdb -U postgres care -f"
	docker compose exec db sh -c "createdb -U postgres care"

ruff-all:
	ruff check .

ruff-fix-all:
	ruff check --fix .

ruff:
	ruff check --fix $(shell git diff --name-only --staged | grep -E '\.py$$|\/pyproject.toml$$')

ruff-all-docker:
	docker exec care bash -c "ruff check ."

ruff-docker:
	docker exec care bash -c "ruff check --fix $(shell git diff --name-only --staged | grep -E '\.py$$|\/pyproject.toml$$')"

%:
	docker compose exec backend bash -c "python manage.py $*"
