#!/bin/bash

set -euo pipefail

STACK_NAME="care"
COMPOSE_FILE="docker-compose.swarm.yaml"
DEPLOYMENT_MODE=""

print_header() {
    echo "Docker Swarm Deployment"
    echo "======================="
    echo ""
}

check_docker() {
    if ! docker --version >/dev/null 2>&1; then
        echo "Docker not installed or not running"
        exit 1
    fi
}

choose_deployment_mode() {
    echo "Choose deployment mode:"
    echo ""
    echo "1. Single-node deployment (everything on one machine)"
    echo "2. Multi-node deployment (Docker-in-Docker simulation)"
    echo ""
    while true; do
        read -p "Select deployment mode: " choice
        case $choice in
            1)
                DEPLOYMENT_MODE="single"
                break
                ;;
            2)
                DEPLOYMENT_MODE="multi"
                break
                ;;
            *)
                echo "Invalid choice. Please enter 1 or 2."
                ;;
        esac
    done
    echo ""
}

# =====================================================
# SINGLE-NODE DEPLOYMENT FUNCTIONS
# =====================================================
init_single_node_swarm() {
    if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -q "active"; then
        echo "Initializing Docker Swarm..."
        docker swarm init --advertise-addr 127.0.0.1 2>/dev/null || docker swarm init
        echo "Swarm initialized."
    fi

    echo ""
    echo "Current nodes:"
    docker node ls
    echo ""
}

# =====================================================
# MULTI-NODE DEPLOYMENT FUNCTIONS
# =====================================================
create_dind_nodes() {
    echo "Creating Docker-in-Docker nodes..."

    # Clean up any existing setup
    cleanup_multi_node

    # Create network for the swarm
    docker network create --driver bridge swarm-net 2>/dev/null || true

    # Create manager node with exposed ports
    docker run -d \
        --name swarm-manager \
        --hostname swarm-manager \
        --privileged \
        --network swarm-net \
        -p 2378:2377 \
        -p 7947:7946 \
        -p 4790:4789 \
        -p 80:80 \
        -p 8080:8080 \
        -p 9100:9100 \
        -p 9101:9101 \
        docker:dind >/dev/null

    # Create worker nodes
    for i in {1..2}; do
        docker run -d \
            --name swarm-worker-$i \
            --hostname swarm-worker-$i \
            --privileged \
            --network swarm-net \
            docker:dind >/dev/null
    done

    echo "Waiting for Docker daemon to start in containers..."
    sleep 15
}

setup_multi_node_swarm() {
    echo "Setting up multi-node Docker Swarm..."

    # Initialize swarm on manager
    manager_ip=$(docker inspect swarm-manager --format '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
    docker exec swarm-manager docker swarm init --advertise-addr $manager_ip >/dev/null

    # Get join token and add workers
    join_token=$(docker exec swarm-manager docker swarm join-token worker -q)
    for i in {1..2}; do
        docker exec swarm-worker-$i docker swarm join --token $join_token $manager_ip:2377 >/dev/null
    done

    echo "Multi-node swarm cluster created!"
}

label_multi_node() {
    echo "Labeling multi-node cluster..."

    # Label nodes for specialized tiers
    worker1_id=$(docker exec swarm-manager docker node ls --filter "name=swarm-worker-1" --format "{{.ID}}")
    docker exec swarm-manager docker node update --label-add tier=data $worker1_id >/dev/null

    worker2_id=$(docker exec swarm-manager docker node ls --filter "name=swarm-worker-2" --format "{{.ID}}")
    docker exec swarm-manager docker node update --label-add tier=application $worker2_id >/dev/null

    echo "Nodes labeled for specialized tiers!"
}

show_multi_node_status() {
    echo "Multi-Node Cluster Status:"
    docker exec swarm-manager docker node ls
    echo ""
    echo "Node Architecture:"
    echo "   swarm-manager: Manager (Orchestration + Traefik)"
    echo "   swarm-worker-1: Data Tier (PostgreSQL, Redis, MinIO)"
    echo "   swarm-worker-2: Application Tier (Django, Celery)"
    echo ""
}

cleanup_multi_node() {
    docker rm -f swarm-manager swarm-worker-1 swarm-worker-2 2>/dev/null || true
    docker network rm swarm-net 2>/dev/null || true
}

deploy_to_multi_node() {
    docker cp "$COMPOSE_FILE" swarm-manager:/"$COMPOSE_FILE" 2>/dev/null
    echo "Deploying to multi-node cluster..."
    docker exec swarm-manager docker stack deploy -c "$COMPOSE_FILE" "$STACK_NAME" >/dev/null
}

# =====================================================
# COMMON DEPLOYMENT FUNCTIONS
# =====================================================
prepare_single_node_compose() {
    echo "Preparing single-node compose file..."

    SINGLE_NODE_COMPOSE="/tmp/docker-compose.single-node.yaml"

    # Remove placement constraints for single-node deployment
    python3 -c "
import yaml
import sys

with open('$COMPOSE_FILE', 'r') as f:
    compose = yaml.safe_load(f)

for service_name, service_config in compose.get('services', {}).items():
    deploy_config = service_config.get('deploy', {})
    placement = deploy_config.get('placement', {})

    if 'constraints' in placement:
        print(f'Removing placement constraints from {service_name}', file=sys.stderr)
        del placement['constraints']

    if not placement and 'placement' in deploy_config:
        del deploy_config['placement']
    if not deploy_config and 'deploy' in service_config:
        del service_config['deploy']

with open('$SINGLE_NODE_COMPOSE', 'w') as f:
    yaml.dump(compose, f, default_flow_style=False, sort_keys=False)
"

    echo "Single-node compose file prepared at $SINGLE_NODE_COMPOSE"
}

deploy_stack() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        echo "Compose file $COMPOSE_FILE not found"
        exit 1
    fi

    if [ "$DEPLOYMENT_MODE" = "single" ]; then
        prepare_single_node_compose
        echo "Deploying stack '$STACK_NAME' to single node..."
        docker stack deploy -c "$SINGLE_NODE_COMPOSE" "$STACK_NAME"
    else
        deploy_to_multi_node
    fi
    echo "Stack deployment initiated"
}

wait_for_services() {
    echo "Waiting for services to become ready..."

    if [ "$DEPLOYMENT_MODE" = "single" ]; then
        docker_cmd="docker"
    else
        docker_cmd="docker exec swarm-manager docker"
    fi

    for attempt in {1..15}; do
        ready=0
        total=0

        while IFS= read -r line; do
            if [[ $line =~ ([0-9]+)/([0-9]+) ]]; then
                replicas_ready=${BASH_REMATCH[1]}
                replicas_total=${BASH_REMATCH[2]}
                total=$((total + replicas_total))
                ready=$((ready + replicas_ready))
            fi
        done < <($docker_cmd service ls --filter "label=com.docker.stack.namespace=$STACK_NAME" --format "{{.Replicas}}" 2>/dev/null)

        if [ "$ready" -eq "$total" ] && [ "$total" -gt 0 ]; then
            echo "All services are ready ($ready/$total)"
            return 0
        fi

        echo "   Attempt $attempt/15: $ready/$total services ready"
        sleep 10
    done

    echo "Timeout waiting for all services to be ready"
    echo "   Use './scripts/deploy-swarm.sh status' to check service status"
    return 1
}

show_status() {
    echo ""
    echo "Stack Status:"
    echo "============="

    if [ "$DEPLOYMENT_MODE" = "single" ]; then
        docker_cmd="docker"
    else
        docker_cmd="docker exec swarm-manager docker"
    fi

    $docker_cmd stack services "$STACK_NAME"
    echo ""
    echo "Service Tasks:"
    echo "=============="
    $docker_cmd stack ps "$STACK_NAME" --no-trunc

    echo ""
    echo "Access URLs:"
    echo "============"
    echo "   Care Application: http://care.localhost"
    echo "   MinIO Console: http://localhost:9101"
    echo "   Traefik Dashboard: http://localhost:8080"

    if [ "$DEPLOYMENT_MODE" = "multi" ]; then
        echo ""
        show_multi_node_status
    fi
}

# =====================================================
# SERVICE MANAGEMENT FUNCTIONS
# =====================================================
show_logs() {
    if [ -z "${1:-}" ]; then
        echo "Error: Service name is required"
        echo "Usage: $0 logs <service_name>"
        echo ""
        echo "Available services:"
        if [ "$DEPLOYMENT_MODE" = "single" ]; then
            docker service ls --filter "label=com.docker.stack.namespace=$STACK_NAME" --format "{{.Name}}" | sed "s/${STACK_NAME}_//"
        else
            docker exec swarm-manager docker service ls --filter "label=com.docker.stack.namespace=$STACK_NAME" --format "{{.Name}}" | sed "s/${STACK_NAME}_//"
        fi
        return 1
    fi

    service_name="$1"

    if [ "$DEPLOYMENT_MODE" = "single" ]; then
        docker_cmd="docker"
    else
        docker_cmd="docker exec swarm-manager docker"
    fi

    echo "Showing logs for ${STACK_NAME}_${service_name}..."

    if ! $docker_cmd service ls --filter "name=${STACK_NAME}_${service_name}" --format "{{.Name}}" | grep -q "${STACK_NAME}_${service_name}"; then
        echo "Service ${STACK_NAME}_${service_name} not found"
        echo "Available services:"
        $docker_cmd service ls --filter "label=com.docker.stack.namespace=$STACK_NAME" --format "{{.Name}}"
        return 1
    fi

    $docker_cmd service logs -f "${STACK_NAME}_${service_name}"
}

scale_service() {
    if [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
        echo "Error: Service name and replica count are required"
        echo "Usage: $0 scale <service_name> <replica_count>"
        echo ""
        echo "Available services:"
        if [ "$DEPLOYMENT_MODE" = "single" ]; then
            docker service ls --filter "label=com.docker.stack.namespace=$STACK_NAME" --format "{{.Name}}" | sed "s/${STACK_NAME}_//"
        else
            docker exec swarm-manager docker service ls --filter "label=com.docker.stack.namespace=$STACK_NAME" --format "{{.Name}}" | sed "s/${STACK_NAME}_//"
        fi
        return 1
    fi

    service_name="$1"
    replicas="$2"

    if [ "$DEPLOYMENT_MODE" = "single" ]; then
        docker_cmd="docker"
    else
        docker_cmd="docker exec swarm-manager docker"
    fi

    echo "Scaling ${STACK_NAME}_${service_name} to $replicas replicas..."

    if ! $docker_cmd service ls --filter "name=${STACK_NAME}_${service_name}" --format "{{.Name}}" | grep -q "${STACK_NAME}_${service_name}"; then
        echo "Service ${STACK_NAME}_${service_name} not found"
        echo "Available services:"
        $docker_cmd service ls --filter "label=com.docker.stack.namespace=$STACK_NAME" --format "{{.Name}}"
        return 1
    fi

    $docker_cmd service scale "${STACK_NAME}_${service_name}=${replicas}"
    echo "Service scaled to $replicas replicas"
}

restart_service() {
    if [ -z "${1:-}" ]; then
        echo "Error: Service name is required"
        echo "Usage: $0 restart <service_name>"
        echo ""
        echo "Available services:"
        if [ "$DEPLOYMENT_MODE" = "single" ]; then
            docker service ls --filter "label=com.docker.stack.namespace=$STACK_NAME" --format "{{.Name}}" | sed "s/${STACK_NAME}_//"
        else
            docker exec swarm-manager docker service ls --filter "label=com.docker.stack.namespace=$STACK_NAME" --format "{{.Name}}" | sed "s/${STACK_NAME}_//"
        fi
        return 1
    fi

    service_name="$1"

    if [ "$DEPLOYMENT_MODE" = "single" ]; then
        docker_cmd="docker"
    else
        docker_cmd="docker exec swarm-manager docker"
    fi

    echo "Restarting service ${STACK_NAME}_${service_name}..."
    $docker_cmd service update --force "${STACK_NAME}_${service_name}"
    echo "Service restart initiated"
}

# =====================================================
# MAIN DEPLOYMENT LOGIC
# =====================================================
main_deploy() {
    print_header
    check_docker
    choose_deployment_mode

    # Cleanup handler for temporary files
    trap 'rm -f /tmp/docker-compose.single-node.yaml 2>/dev/null || true' EXIT

    if [ "$DEPLOYMENT_MODE" = "single" ]; then
        echo "Setting up single-node deployment..."
        init_single_node_swarm
    else
        echo "Setting up multi-node deployment..."
        create_dind_nodes
        setup_multi_node_swarm
        label_multi_node
        show_multi_node_status
    fi

    deploy_stack
    wait_for_services
    show_status

    echo ""
    echo "Deployment completed successfully!"
    echo "Use './scripts/deploy-swarm.sh status' to check services anytime"
}

remove_stack() {
    if [ "$DEPLOYMENT_MODE" = "multi" ] || docker ps --format "{{.Names}}" | grep -q "swarm-manager"; then
        echo "Removing multi-node stack '$STACK_NAME'..."
        docker exec swarm-manager docker stack rm "$STACK_NAME" 2>/dev/null || true

        echo "Waiting for stack removal to complete..."
        sleep 10

        echo "Cleaning up multi-node Docker-in-Docker setup..."
        cleanup_multi_node

        echo "Multi-node stack and infrastructure removed"
    else
        echo "Removing single-node stack '$STACK_NAME'..."
        docker stack rm "$STACK_NAME"

        echo "Waiting for stack removal to complete..."
        sleep 10

        echo "Removing volumes..."
        # Remove the specific volumes used by the care stack
        docker volume rm ${STACK_NAME}_minio-data ${STACK_NAME}_postgres-data ${STACK_NAME}_redis-data 2>/dev/null || true

        # Clean up temporary files
        rm -f /tmp/docker-compose.single-node.yaml 2>/dev/null || true

        echo "Single-node stack and volumes removed"
    fi
}

detect_deployment_mode() {
    if docker ps --format "{{.Names}}" | grep -q "swarm-manager"; then
        DEPLOYMENT_MODE="multi"
    else
        DEPLOYMENT_MODE="single"
    fi
}

# =====================================================
# COMMAND HANDLING
# =====================================================
case "${1:-deploy}" in
    deploy)
        main_deploy
        ;;
    remove)
        detect_deployment_mode
        remove_stack
        ;;
    status)
        detect_deployment_mode
        show_status
        ;;
    logs)
        detect_deployment_mode
        show_logs "${2:-}"
        ;;
    scale)
        detect_deployment_mode
        scale_service "${2:-}" "${3:-}"
        ;;
    restart)
        detect_deployment_mode
        restart_service "${2:-}"
        ;;
    update)
        detect_deployment_mode
        echo "Updating stack '$STACK_NAME'..."
        if [ "$DEPLOYMENT_MODE" = "single" ]; then
            prepare_single_node_compose
            docker stack deploy -c "$SINGLE_NODE_COMPOSE" "$STACK_NAME"
        else
            deploy_to_multi_node
        fi
        echo "Stack update completed"
        ;;
    *)
        echo ""
        echo "Commands:"
        echo "  deploy      - Deploy the Care stack (choose single or multi-node)"
        echo "  remove      - Remove the Care stack, volumes, and cleanup infrastructure"
        echo "  status      - Show stack status and access URLs"
        echo "  logs        - Show service logs"
        echo "  scale       - Scale a service"
        echo "  restart     - Force restart a service"
        echo "  update      - Update the stack with current compose file"
        echo ""
        ;;
esac
