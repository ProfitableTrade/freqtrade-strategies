#!/usr/bin/env bash

# source
source config.env

# export
echo DOMAIN=${DOMAIN} > .env

# traefik
ACME_FILE=.acme.json

([[ -f "$ACME_FILE" ]] && echo "✅ $ACME_FILE file exist" || echo "{}" > "$ACME_FILE") || echo "❌ fail to make file $ACME_FILE"
chmod 600 "$ACME_FILE" && echo "✅ $ACME_FILE set 600 permissions" || echo "❌ fail to set permissions $ACME_FILE"

# start
docker compose up -d
