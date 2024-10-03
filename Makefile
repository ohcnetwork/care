.PHONY: build, re-build, up, down, list, logs, test, makemigrations, reset_db


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

up:
	docker compose -f docker-compose.yaml -f $(docker_config_file) up -d --wait

down:
	docker compose -f docker-compose.yaml -f $(docker_config_file) down

load-dummy-data:
	docker compose exec backend bash -c "python manage.py load_dummy_data"

list:
	docker compose -f docker-compose.yaml -f $(docker_config_file) ps

logs:
	docker compose -f docker-compose.yaml -f $(docker_config_file) logs

checkmigration:
	docker compose exec backend bash -c "python manage.py makemigrations --check --dry-run"

makemigrations:
	docker compose exec backend bash -c "python manage.py makemigrations"

test:
	docker compose exec backend bash -c "python manage.py test --keepdb --parallel --shuffle"

test-coverage:
	docker compose exec backend bash -c "coverage run manage.py test --settings=config.settings.test --keepdb --parallel --shuffle"
	docker compose exec backend bash -c "coverage combine || true; coverage xml"
	docker compose cp backend:/app/coverage.xml coverage.xml

reset_db:
	docker compose exec backend bash -c "python manage.py reset_db --noinput"
	docker compose exec backend bash -c "python manage.py migrate"

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
