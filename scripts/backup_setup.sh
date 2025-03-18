#!/bin/bash

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Unsupported OS"
    exit 1
fi

# Package lists for Debian-based systems
debian_packages=("cron" "msmtp" "mailutils")

# Package lists for Fedora-based systems
fedora_packages=("cronie" "msmtp" "mailx")

check_debian() {
    all_installed=true
    for pkg in "${debian_packages[@]}"; do
        if dpkg -l | grep -q "^ii  $pkg "; then
            echo "$pkg is installed."
        else
            echo "$pkg is NOT installed."
            all_installed=false
        fi
    done

    if $all_installed; then
        sudo systemctl enable --now cron
        check_path
        echo "Setting up cron job..."
        (crontab -l 2>/dev/null; echo "0 0 * * * /scripts/backup.sh") | crontab -

        # Verify cron job
        echo "Cron job set up! Current crontab:"
        crontab -l
    else
        echo "Some packages are missing."
    fi
}

# Function to check packages on Fedora-based systems
check_fedora() {
    all_installed=true
    for pkg in "${fedora_packages[@]}"; do
        if rpm -q "$pkg" &>/dev/null; then
            echo "$pkg is installed."
        else
            echo "$pkg is NOT installed."
            all_installed=false
        fi
    done

    if $all_installed; then
        sudo systemctl enable --now crond
        # Set up the cron job to run the backup script daily at midnight
        check_path
        echo "Setting up cron job..."
        (crontab -l 2>/dev/null; echo "0 0 * * * /scripts/backup.sh") | crontab -

        # Verify cron job
        echo "Cron job set up! Current crontab:"
        crontab -l

    else
        echo "Some packages are missing. Skipping additional commands."
    fi
}

check_path(){
    if [ ! -f "/scripts/backup.sh" ]; then
        echo "Error: /scripts/backup.sh does not exist"
        echo "Please navigate to the 'care' directory"
        exit 1
    fi
}

case "$OS" in
    debian|ubuntu)
        echo "Detected Debian-based system"
        check_debian
    ;;
    fedora|centos)
        echo "Detected Fedora-based system"
        check_fedora
    ;;
    *)
        echo "Unsupported Linux distribution: $OS"
        exit 1
    ;;
esac
