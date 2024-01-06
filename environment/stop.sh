#!/usr/bin/env bash

# check
if [ ! -f .env ]; then
    echo "File .env not found! Skip!"
    exit 0
fi

# env
source .env
source config.env

# stop
docker compose down
