#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset
set -o xtrace


python manage.py migrate
daphne config.asgi:channel_layer --port 8000 --bind 0.0.0.0
python manage.py runworker --settings=config.settings.local
