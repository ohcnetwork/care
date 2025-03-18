#!/bin/bash

# Check if crontab command is available
if ! command -v crontab &> /dev/null; then
    echo "Error: 'crontab' command not found. Please install cron or crontab utility."
    exit 1
fi
