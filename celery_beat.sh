#!/bin/bash

celery --app=config.celery_app --loglevel=info beat
