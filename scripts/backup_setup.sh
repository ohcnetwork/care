#!/bin/bash

# Function to check if a package is installed
is_installed() {
    command -v "$1" >/dev/null 2>&1
}

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Unsupported OS"
    exit 1
fi

# Install packages based on the detected OS
case "$OS" in
    debian|ubuntu)
        echo "Detected Debian-based system. Installing packages..."
        sudo apt update && sudo apt install -y libnotify-bin cron msmtp mailutils
        sudo systemctl enable --now cron
        ;;
    fedora|centos)
        echo "Detected Fedora-based system. Installing packages..."
        sudo dnf install -y libnotify cronie msmtp mailx
        sudo systemctl enable --now crond
        ;;
    *)
        echo "Unsupported Linux distribution: $OS"
        exit 1
        ;;
esac

echo "Installation completed successfully!"
echo "---------------------------------------"
# Set up the cron job to run the backup script daily at midnight
echo "Setting up cron job..."
(crontab -l 2>/dev/null; echo "0 0 * * * /scripts/backup.sh") | crontab -

# Verify cron job
echo "Cron job set up! Current crontab:"
crontab -l
