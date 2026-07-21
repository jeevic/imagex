#!/usr/bin/env bash

export MODE=prod

uv run gunicorn -c gunicorn.conf.py main:app