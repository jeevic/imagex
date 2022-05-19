#!/usr/bin/env bash

export MODE=prod

gunicorn -c gunicorn.conf.py main:app