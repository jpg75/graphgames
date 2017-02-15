#!/bin/sh
celery worker -A app.celery --loglevel=info