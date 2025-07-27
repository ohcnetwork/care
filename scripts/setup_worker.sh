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
    sudo mkdir -p "$GLUSTER_BRICK_DIR"
    sudo chown -R "$USER":"$USER" "$GLUSTER_SHARED_DIR"
    sudo chown -R "$USER":"$USER" "$GLUSTER_BRICK_DIR"
    echo "Base directories created"
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

join_swarm_worker() {
    echo ">>> Joining Docker Swarm (as worker)..."

    if docker node ls &>/dev/null; then
        echo "Already part of a Swarm"
        return
    fi

    echo "Enter the 'docker swarm join' command for worker:"
    read -p "> " join_command

    if [[ -n "$join_command" ]]; then
        eval "$join_command"
        echo "Joined swarm as worker"
    else
        echo "No join command provided"
        exit 1
    fi
}

### GLUSTERFS SETUP ###

setup_glusterfs() {
    echo ">>> Setting up GlusterFS server..."
    sudo systemctl start glusterd
    sudo systemctl enable glusterd
    echo "GlusterFS server setup complete"
}

add_gluster_hosts() {
    echo ">>> Adding GlusterFS nodes to /etc/hosts..."
    for node in manager-1 worker-1 worker-2; do
        read -p "${node^} private IP (Enter to skip): " node_ip
        if [[ -n "$node_ip" ]]; then
            add_host_entry "$node_ip" "$node"
        fi
    done
    echo "GlusterFS nodes added"
}

mount_glusterfs() {
    echo ">>> Mounting GlusterFS volume..."
    # Try to use manager-1 first, then fallback to workers
    local mount_hosts=("manager-1" "worker-1" "worker-2")
    for host in "${mount_hosts[@]}"; do
        if ping -c 1 "$host" &>/dev/null; then
            if ! mountpoint -q "$GLUSTER_SHARED_DIR"; then
                sudo mount -t glusterfs "$host:/$GLUSTER_VOLUME_NAME" "$GLUSTER_SHARED_DIR" 2>/dev/null && {
                    local fstab_entry="$host:/$GLUSTER_VOLUME_NAME $GLUSTER_SHARED_DIR glusterfs defaults,_netdev 0 0"
                    if ! grep -q "$GLUSTER_VOLUME_NAME" /etc/fstab; then
                        echo "$fstab_entry" | sudo tee -a /etc/fstab
                    fi
                    echo "GlusterFS mounted via $host"
                    # Create data subdirectories AFTER mounting
                    echo ">>> Creating data subdirectories..."
                    sudo mkdir -p "$GLUSTER_SHARED_DIR"/{postgres-master,postgres-slave1,postgres-slave2,redis,minio,letsencrypt,portainer}
                    sudo chown -R "$USER":"$USER" "$GLUSTER_SHARED_DIR"
                    echo "Data directories created in mounted volume"
                    return
                }
            else
                echo "Mount point already active"
                return
            fi
        fi
    done
    echo "Could not mount GlusterFS - no GlusterFS nodes reachable"
}

### ORCHESTRATION ###

echo ">>> Starting Docker Swarm Worker Setup..."

system_update
install_docker
create_directories
setup_glusterfs
add_gluster_hosts
join_swarm_worker
mount_glusterfs

echo "Worker setup complete"
