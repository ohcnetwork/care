#!/bin/bash

set -euo pipefail

STACK_NAME="care"
COMPOSE_FILE="docker-compose.swarm.yaml"
GLUSTER_VOLUME_NAME="care-volume"
GLUSTER_BRICK_DIR="/care-storage/brick"
GLUSTER_SHARED_DIR="/care-storage/shared"

### SYSTEM SETUP ###

system_update() {
    echo ">>> Updating system packages..."
    sudo apt update -y >/dev/null 2>&1
    sudo apt upgrade -y >/dev/null 2>&1
    sudo apt install -y net-tools build-essential git curl wget glusterfs-server glusterfs-client >/dev/null 2>&1
    echo "System packages updated"
}

install_docker() {
    echo ">>> Checking Docker installation..."
    if command -v docker &> /dev/null; then
        echo "Docker already installed"
        return
    fi

    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sudo sh &> /dev/null
    sudo usermod -aG docker $USER &> /dev/null
    echo "Docker installed"
}

create_directories() {
    echo ">>> Creating CARE data directories..."
    sudo mkdir -p "$GLUSTER_SHARED_DIR"/{postgres,redis,minio}
    sudo chown -R $USER:$USER "$GLUSTER_SHARED_DIR"
    echo "CARE directories created"
}

### NETWORK / HOST CONFIG ###

get_private_ip() {
    hostname -I | awk '{print $1}'
}

get_public_ip() {
    curl -s http://checkip.amazonaws.com || echo ""
}

get_node_info() {
    echo
    echo "Current node information:"
    echo "Public IP: $(get_public_ip)"
    echo "Private IP: $(get_private_ip)"
    echo "Hostname: $(hostname)"
    echo
}

add_host_entry() {
    local ip="$1"
    local hostname="$2"

    echo ">>> Adding host entry: $hostname ($ip)..."

    if ! grep -q "$hostname" /etc/hosts; then
        echo "$ip $hostname" | sudo tee -a /etc/hosts
        echo "Added $hostname ($ip) to /etc/hosts"
    else
        echo "$hostname already exists in /etc/hosts"
    fi
}

### DOCKER SWARM SETUP ###

init_swarm_leader() {
    echo ">>> Initializing Docker Swarm (leader node)..."
    local private_ip=$(get_private_ip)

    if docker node ls &>/dev/null; then
        echo "Swarm already active on this node"
        return
    fi

    docker swarm init --advertise-addr "$private_ip"
    echo "Swarm initialized as leader"
    echo
    echo "=== JOIN TOKENS ==="
    echo "For MANAGERS:"
    docker swarm join-token manager
    echo
    echo "For WORKERS:"
    docker swarm join-token worker
}

join_swarm_manager() {
    echo ">>> Joining Docker Swarm (as manager)..."

    if docker node ls &>/dev/null; then
        echo "Already part of a Swarm"
        return
    fi

    echo "Enter the 'docker swarm join' command for manager:"
    read -p "> " join_command

    if [[ -n "$join_command" ]]; then
        eval "$join_command"
        echo "Joined swarm as manager"
    else
        echo "No join command provided"
        exit 1
    fi
}

### GLUSTERFS SETUP ###

setup_glusterfs() {
    echo ">>> Setting up GlusterFS..."
    sudo systemctl start glusterd
    sudo systemctl enable glusterd
    sudo mkdir -p "$GLUSTER_BRICK_DIR"
    sudo mkdir -p "$GLUSTER_SHARED_DIR"
    echo "GlusterFS setup complete"
}

setup_gluster_cluster() {
    local is_first_node="$1"
    local private_ip=$(get_private_ip)

    echo ">>> Setting up GlusterFS cluster config..."
    read -p "Enter this node's manager number: " manager_num
    local this_manager="manager-$manager_num"
    add_host_entry "$private_ip" "$this_manager"

    if [[ "$is_first_node" == "true" ]]; then
        echo ">>> Initializing GlusterFS cluster as first manager..."

        managers=()
        for i in {2..3}; do
            read -p "Manager $i private IP (Enter to skip): " manager_ip
            if [[ -n "$manager_ip" ]]; then
                managers+=("$manager_ip")
                add_host_entry "$manager_ip" "manager-$i"
            fi
        done

        if [[ ${#managers[@]} -gt 0 ]]; then
            echo "Waiting for other nodes..."
            sleep 30

            for i in "${!managers[@]}"; do
                sudo gluster peer probe "${managers[$i]}" || true
            done

            local volume_bricks="$private_ip:$GLUSTER_BRICK_DIR"
            for i in {2..3}; do
                if [[ -n "${managers[$((i-2))]}" ]]; then
                    volume_bricks+=" ${managers[$((i-2))]}:$GLUSTER_BRICK_DIR"
                fi
            done

            sudo gluster volume create "$GLUSTER_VOLUME_NAME" replica 3 $volume_bricks force
            sudo gluster volume start "$GLUSTER_VOLUME_NAME"
            echo "GlusterFS volume created"
        fi
    else
        echo ">>> Configuring GlusterFS brick as additional manager..."
        for i in {1..3}; do
            if [[ "$i" == "$manager_num" ]]; then
                continue
            fi
            read -p "Manager $i private IP (Enter to skip): " manager_ip
            if [[ -n "$manager_ip" ]]; then
                add_host_entry "$manager_ip" "manager-$i"
            fi
        done
        echo "GlusterFS brick ready"
    fi
}

mount_glusterfs() {
    echo ">>> Mounting GlusterFS volume..."

    local private_ip=$(get_private_ip)

    if sudo gluster volume info "$GLUSTER_VOLUME_NAME" &>/dev/null; then
        if ! mountpoint -q "$GLUSTER_SHARED_DIR"; then
            sudo mount -t glusterfs "$private_ip:/$GLUSTER_VOLUME_NAME" "$GLUSTER_SHARED_DIR"

            local fstab_entry="$private_ip:/$GLUSTER_VOLUME_NAME $GLUSTER_SHARED_DIR glusterfs defaults,_netdev 0 0"
            if ! grep -q "$GLUSTER_VOLUME_NAME" /etc/fstab; then
                echo "$fstab_entry" | sudo tee -a /etc/fstab
            fi

            echo "GlusterFS mounted"
        else
            echo "Mount point already active"
        fi
    else
        echo "GlusterFS volume not found"
    fi
}

### STACK DEPLOYMENT ###

deploy_stack() {
    echo ">>> Deploying CARE stack..."

    if [ ! -f "$COMPOSE_FILE" ]; then
        echo "Compose file $COMPOSE_FILE not found"
        exit 1
    fi

    docker stack deploy -c "$COMPOSE_FILE" "$STACK_NAME"
    echo "Stack deployed"
}

remove_stack() {
    echo ">>> Removing CARE stack..."
    docker stack rm "$STACK_NAME" 2>/dev/null || true
    sleep 10
    docker volume rm ${STACK_NAME}_minio-data ${STACK_NAME}_postgres-data ${STACK_NAME}_redis-data 2>/dev/null || true
    echo "Stack removed"
}

### ORCHESTRATION ###

setup_manager() {
    local node_type="$1"

    echo ">>> Starting Docker Swarm Manager Setup..."
    get_node_info

    system_update
    install_docker
    create_directories
    setup_glusterfs

    if [[ "$node_type" == "first" ]]; then
        init_swarm_leader
        setup_gluster_cluster "true"
    else
        join_swarm_manager
        setup_gluster_cluster "false"
    fi

    mount_glusterfs
    echo "Manager setup complete"
}

main() {
    case "${1:-}" in
        "first")
            setup_manager "first"
            ;;
        "additional")
            setup_manager "additional"
            ;;
        "deploy")
            deploy_stack
            ;;
        "remove")
            remove_stack
            ;;
        *)
            exit 1
            ;;
    esac
}

main "$@"
