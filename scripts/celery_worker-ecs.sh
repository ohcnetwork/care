#!/bin/bash
echo "This script is deprecated. Use celery_worker.sh instead."
exec "$(dirname "$0")/celery_worker.sh"
