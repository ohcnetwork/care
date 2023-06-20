#!/bin/bash

celery --app=config.celery_app beat --loglevel=info
