#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py collectstatic --noinput
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py migrate
