.PHONY: build, re-build, up, down, list, logs, test, makemigrations

 
DOCKER_VERSION := $(shell docker --version 2>/dev/null)
DOCKER_COMPOSE_VERSION := $(shell docker-compose --version 2>/dev/null)

docker_config_file = 'docker-compose.local.yaml'

all:
ifndef DOCKER_VERSION
    $(error "command docker is not available, please install Docker")
endif
ifndef DOCKER_COMPOSE_VERSION
    $(error "command docker-compose is not available, please install Docker")
endif

re-build:
	docker-compose -f $(docker_config_file) build --no-cache

build:
	docker-compose -f $(docker_config_file) build

up:
	docker network inspect care >/dev/null 2>&1 || \
		docker network create care 
	docker-compose -f $(docker_config_file) up -d

down:
	docker-compose -f $(docker_config_file) down

list:
	docker-compose -f $(docker_config_file) ps

logs:
	docker-compose -f $(docker_config_file) logs

makemigrations: up
	docker exec care bash -c "python manage.py makemigrations"

test: up
	docker exec care bash -c "python manage.py test --keepdb"

test_coverage: up
	docker exec care bash -c "coverage run manage.py test --settings=config.settings.test --keepdb"
	docker exec care bash -c "coverage report"
