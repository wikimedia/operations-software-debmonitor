#!/bin/bash
export DEBMONITOR_CONFIG=/etc/debmonitor/config.json
export DJANGO_SETTINGS_MODULE=debmonitor.settings.prod

cd /usr/lib/python3/dist-packages/debmonitor/
python3 manage.py $@