.PHONY: build, re-build, up, down, list, logs, test, makemigrations


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
	docker compose -f docker-compose.yaml -f $(docker_config_file) up -d

down:
	docker compose -f docker-compose.yaml -f $(docker_config_file) down

list:
	docker compose -f docker-compose.yaml -f $(docker_config_file) ps

logs:
	docker compose -f docker-compose.yaml -f $(docker_config_file) logs

checkmigration: up
	docker compose exec backend bash -c "python manage.py makemigrations --check --dry-run"

makemigrations: up
	docker compose exec backend bash -c "python manage.py makemigrations"

test: up
	docker compose exec backend bash -c "python manage.py test --keepdb --parallel"

test-coverage: up
	docker compose exec backend bash -c "coverage run manage.py test --settings=config.settings.test --keepdb --parallel"
	docker compose exec backend bash -c "coverage combine || true; coverage xml"
	docker compose cp backend:/app/coverage.xml coverage.xml

ruff-all:
	ruff --config pyproject.toml check .

ruff:
	ruff --config pyproject.toml --fix $(shell git diff --name-only --staged | grep -E '\.py$$|\/pyproject.toml$$')

ruff-all-docker:
	docker exec care bash -c "ruff --config pyproject.toml check ."

ruff-docker:
	docker exec care bash -c "ruff --config pyproject.toml --fix $(shell git diff --name-only --staged | grep -E '\.py$$|\/pyproject.toml$$')"
