#!/usr/bin/env bash
cd "$(dirname "$0")"
if [ ! -d "venv" ]; then
    bash install.sh
else
    ./venv/bin/python3 -m backend.app
fi
