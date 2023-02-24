#!/bin/bash

set -e

poetry install --sync

python app/allocation/entrypoints/run_worker.py