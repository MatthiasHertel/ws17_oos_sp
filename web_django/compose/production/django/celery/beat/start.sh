#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset


celery -A django_playground.taskapp beat -l INFO
