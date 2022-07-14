#!/bin/bash
/bin/bash -c -- celery --app=config.celery_app --loglevel=info beat
