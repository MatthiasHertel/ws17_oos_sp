#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset


python /app/manage.py collectstatic --noinput
daphne config.asgi:channel_layer --port 8000 --bind 0.0.0.0
python /app/manage.py runworker --settings=config.settings.production
