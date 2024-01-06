#!/usr/bin/env bash

# source
source config.env

# export
echo DOMAIN=${DOMAIN} > .env
echo MONGODB_USERNAME=${MONGODB_USERNAME} >> .env
echo MONGODB_PASSWORD=${MONGODB_PASSWORD} >> .env

# start
docker compose up -d
