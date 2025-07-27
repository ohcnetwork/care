#!/bin/bash
set -euo pipefail

GLUSTER_SHARED_DIR="/care-storage/shared"
GLUSTER_BRICK_DIR="/care-storage/brick"
GLUSTER_VOLUME_NAME="care-volume"

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
    sudo usermod -aG docker ubuntu &> /dev/null
    echo "Docker installed"
}

create_directories() {
    echo ">>> Creating base directories..."
    sudo mkdir -p "$GLUSTER_SHARED_DIR"
    sudo chown -R "$USER":"$USER" "$GLUSTER_SHARED_DIR"
    echo "Base directories created"
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
    echo ">>> Setting up GlusterFS cluster config..."
    local private_ip=$(get_private_ip)

    read -p "Enter this node's manager number (should be 1): " manager_num
    local this_manager="manager-$manager_num"
    add_host_entry "$private_ip" "$this_manager"

    echo ">>> Initializing GlusterFS cluster as first manager..."

    workers=()
    for i in 1 2; do
        read -p "Worker $i private IP (Enter to skip): " worker_ip
        if [[ -n "$worker_ip" ]]; then
            workers+=("$worker_ip")
            add_host_entry "$worker_ip" "worker-$i"
        fi
    done

    if [[ ${#workers[@]} -gt 0 ]]; then
        echo "Waiting for worker nodes..."
        sleep 15

        for i in "${!workers[@]}"; do
            sudo gluster peer probe "${workers[$i]}" || true
        done

        local volume_bricks="$private_ip:$GLUSTER_BRICK_DIR"
        for i in 0 1; do
            if [[ -n "${workers[$i]}" ]]; then
                volume_bricks+=" ${workers[$i]}:$GLUSTER_BRICK_DIR"
            fi
        done

        sudo gluster volume create "$GLUSTER_VOLUME_NAME" replica 3 $volume_bricks force
        sudo gluster volume start "$GLUSTER_VOLUME_NAME"
        echo "GlusterFS volume created"
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

        # Create data subdirectories AFTER mounting
        echo ">>> Creating data subdirectories..."
        sudo mkdir -p "$GLUSTER_SHARED_DIR"/{postgres-master,postgres-slave1,postgres-slave2,redis,minio,letsencrypt,portainer}
        sudo chown -R "$USER":"$USER" "$GLUSTER_SHARED_DIR"
        echo "Data directories created in mounted volume"
    else
        echo "GlusterFS volume not found"
    fi
}

### ORCHESTRATION ###

echo ">>> Starting Docker Swarm Manager Setup..."

get_node_info
system_update
install_docker
create_directories
setup_glusterfs
init_swarm_leader
setup_gluster_cluster
mount_glusterfs

echo "Manager setup complete"
