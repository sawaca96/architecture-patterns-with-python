#!/bin/bash

set -e

poetry install --sync

python app/allocation/routers/worker.py