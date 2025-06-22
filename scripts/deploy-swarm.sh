#!/bin/bash

set -euo pipefail

STACK_NAME="care"
COMPOSE_FILE="docker-compose.swarm.yaml"

init_swarm() {
    if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -q "active"; then
        echo "Initializing Docker Swarm..."
        docker swarm init --advertise-addr 127.0.0.1 2>/dev/null || docker swarm init
        echo "Swarm initialized"
    fi
}

deploy_stack() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        echo "Compose file $COMPOSE_FILE not found"
        exit 1
    fi

    echo "Deploying stack '$STACK_NAME'..."
    docker stack deploy -c "$COMPOSE_FILE" "$STACK_NAME"
    echo "Stack deployment initiated"
}

show_status() {
    echo "Stack Status:"
    docker stack services "$STACK_NAME"
    echo ""
    echo "Service Tasks:"
    docker stack ps "$STACK_NAME"
}

remove_stack() {
    echo "Removing stack '$STACK_NAME'..."
    docker stack rm "$STACK_NAME"
    sleep 10
    echo "Removing volumes..."
    docker volume rm ${STACK_NAME}_minio-data ${STACK_NAME}_postgres-data ${STACK_NAME}_redis-data 2>/dev/null || true
    echo "Stack removed"
}

main_deploy() {
    echo "Docker Swarm Deployment"
    init_swarm
    deploy_stack
    show_status
    echo "Deployment completed"
}

case "${1:-deploy}" in
    deploy)
        main_deploy
        ;;
    remove)
        remove_stack
        ;;
    status)
        show_status
        ;;
    update)
        echo "Updating stack '$STACK_NAME'..."
        docker stack deploy -c "$COMPOSE_FILE" "$STACK_NAME"
        echo "Stack updated"
        ;;
    *)
        echo "Commands:"
        echo "  deploy  - Deploy the CARE stack"
        echo "  remove  - Remove the CARE stack"
        echo "  status  - Show stack status"
        echo "  update  - Update the stack"
        ;;
esac
