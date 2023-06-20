#!/bin/bash

celery --app=config.celery_app worker --max-tasks-per-child=6 --loglevel=info
