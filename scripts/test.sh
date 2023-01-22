#!/bin/bash
set -x
set -e

ARGS=$@
docker compose build
docker compose run --rm app /bin/bash -c "poetry install --sync && pytest $ARGS"
docker compose down


