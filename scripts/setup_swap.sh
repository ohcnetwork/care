#!/bin/bash

set -euo pipefail

SWAPFILE="/swapfile"
SIZE="2G"

if swapon --show | grep -q "$SWAPFILE"; then
    echo "Swap already active."
    free -h
    exit 0
fi

echo "Creating ${SIZE} swap at $SWAPFILE..."

sudo fallocate -l "$SIZE" "$SWAPFILE"
sudo chmod 600 "$SWAPFILE"
sudo mkswap "$SWAPFILE"
sudo swapon "$SWAPFILE"

if ! grep -q "$SWAPFILE" /etc/fstab; then
    echo "$SWAPFILE none swap sw 0 0" | sudo tee -a /etc/fstab > /dev/null
fi

sudo sysctl -w vm.swappiness=10
if ! grep -q "vm.swappiness" /etc/sysctl.conf; then
    echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf > /dev/null
fi

echo "Swap setup complete."
free -h
