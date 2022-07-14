#!/bin/bash

celery --app=config.celery_app --loglevel=info worker
