#!/bin/bash

set -euo pipefail

GLUSTER_SHARED_DIR="/care-storage/shared"
GLUSTER_VOLUME_NAME="care-volume"

### SYSTEM SETUP ###

system_update() {
    echo ">>> Updating system packages..."
    sudo apt update -y >/dev/null 2>&1
    sudo apt upgrade -y >/dev/null 2>&1
    sudo apt install -y net-tools build-essential git curl wget glusterfs-client >/dev/null 2>&1
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
    echo ">>> Creating shared data directory..."
    sudo mkdir -p "$GLUSTER_SHARED_DIR"
    sudo chown -R $USER:$USER "$GLUSTER_SHARED_DIR"
    echo "Directory created"
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

add_manager_hosts() {
    echo ">>> Adding manager hosts to /etc/hosts..."

    for i in {1..3}; do
        read -p "Manager $i private IP (Enter to skip): " manager_ip
        if [[ -n "$manager_ip" ]]; then
            add_host_entry "$manager_ip" "manager-$i"
        fi
    done

    echo "Manager hosts added"
}

mount_glusterfs() {
    echo ">>> Mounting GlusterFS volume..."

    # Try to use manager-1 first, then fallback to others
    local mount_hosts=("manager-1" "manager-2" "manager-3")

    for host in "${mount_hosts[@]}"; do
        if ping -c 1 "$host" &>/dev/null; then
            if ! mountpoint -q "$GLUSTER_SHARED_DIR"; then
                sudo mount -t glusterfs "$host:/$GLUSTER_VOLUME_NAME" "$GLUSTER_SHARED_DIR" 2>/dev/null && {
                    local fstab_entry="$host:/$GLUSTER_VOLUME_NAME $GLUSTER_SHARED_DIR glusterfs defaults,_netdev 0 0"
                    if ! grep -q "$GLUSTER_VOLUME_NAME" /etc/fstab; then
                        echo "$fstab_entry" | sudo tee -a /etc/fstab
                    fi
                    echo "GlusterFS mounted via $host"
                    return
                }
            else
                echo "Mount point already active"
                return
            fi
        fi
    done

    echo "Could not mount GlusterFS - no managers reachable"
}

### ORCHESTRATION ###

setup_worker() {
    echo ">>> Starting Docker Swarm Worker Setup..."

    system_update
    install_docker
    create_directories
    add_manager_hosts
    join_swarm_worker
    mount_glusterfs

    echo "Worker setup complete"
}

main() {
    setup_worker
}

main
