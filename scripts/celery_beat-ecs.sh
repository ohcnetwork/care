#!/bin/bash
echo "This script is deprecated. Use celery_beat.sh instead."
exec "$(dirname "$0")/celery_beat.sh"
