#!/bin/bash
set -x
set -e

ARGS=$@
poetry install --sync && pytest $ARGS