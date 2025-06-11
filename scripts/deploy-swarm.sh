#!/bin/bash

# TODO: Docker secrets, MinIO, Celery, Traefik services, Logs, scaling, health checks

set -euo pipefail

STACK_NAME="care"
COMPOSE_FILE="docker-compose.swarm.yaml"

check_docker() {
    if ! docker --version >/dev/null 2>&1; then
        echo "Docker not installed or not running"
        exit 1
    fi
}

init_swarm() {
    if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -q "active"; then
        docker swarm init --advertise-addr 127.0.0.1 2>/dev/null || docker swarm init
    fi
}

deploy_stack() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        echo "Compose file $COMPOSE_FILE not found"
        exit 1
    fi
    docker stack deploy -c "$COMPOSE_FILE" "$STACK_NAME"
}

wait_for_services() {
    for attempt in {1..20}; do
        ready=$(docker service ls --filter "label=com.docker.stack.namespace=$STACK_NAME" --format "{{.Replicas}}" | grep -c "1/1")
        total=$(docker service ls --filter "label=com.docker.stack.namespace=$STACK_NAME" | tail -n +2 | wc -l)

        if [ "$ready" -eq "$total" ] && [ "$total" -gt 0 ]; then
            break
        fi

        sleep 5
    done
}

show_status() {
    docker service ls --filter "label=com.docker.stack.namespace=$STACK_NAME"
    docker stack services "$STACK_NAME"
    docker stack ps "$STACK_NAME"
}

main() {
    check_docker
    init_swarm
    deploy_stack
    wait_for_services
    show_status
}

case "${1:-deploy}" in
    deploy) main ;;
    remove) docker stack rm "$STACK_NAME" ;;
    status) show_status ;;
    logs) docker service logs -f "${STACK_NAME}_${2:-backend}" ;;
    scale) docker service scale "${STACK_NAME}_${2:-backend}=${3:-2}" ;;
    *) echo "Usage: $0 {deploy|remove|status|logs [service]|scale [service] [replicas]}" ;;
esac
