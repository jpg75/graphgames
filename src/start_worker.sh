#!/bin/bash
source flaskenv/bin/activate
celery worker -A app.celery --loglevel=info

deactivate
