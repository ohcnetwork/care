#!/bin/bash

celery --app=config.celery_app --max-tasks-per-child 6 --loglevel=info worker
