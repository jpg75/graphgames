#!/bin/sh
source flaskenv/bin/activate
celery worker -A app.celery --loglevel=info