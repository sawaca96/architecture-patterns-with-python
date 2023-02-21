#!/bin/bash

set -e

poetry install --sync

uvicorn app.allocation.entrypoints.api:app --reload --host 0.0.0.0 --port 8000