#!/usr/bin/env bash

# source
source config.env

# export
echo DOMAIN=${DOMAIN} > .env

# start
docker compose up -d
