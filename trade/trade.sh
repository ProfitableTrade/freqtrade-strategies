#!/usr/bin/env bash

set -e

source .env

export DOMAIN=${DOMAIN}
export TRADE_NAME=${TRADE_NAME}
export ENV_NAME=${ENV_NAME}
export STRATEGY=${STRATEGY}
export CONFIG_NAME=${CONFIG_NAME}
export DRY_RUN_WALLET=${DRY_RUN_WALLET}
export RUNTIME_TYPE=${RUNTIME_TYPE}

if [[ "$RUNTIME_TYPE" == "dry-run" ]]; then
  docker compose -f docker-compose-trade.yml \
    run \
    --detach \
    --name ${ENV_NAME}-freqtrade \
    --rm freqtrade trade \
    --strategy ${STRATEGY} \
    --config /freqtrade/user_data/${CONFIG_NAME}.json \
    --dry-run \
    --dry-run-wallet ${DRY_RUN_WALLET}

elif [[ "$RUNTIME_TYPE" == "production" ]]; then
  docker compose -f docker-compose-trade.yml \
    run \
    --detach \
    --name ${ENV_NAME}-freqtrade \
    --rm freqtrade trade \
    --strategy ${STRATEGY} \
    --config /freqtrade/user_data/${CONFIG_NAME}.json

else
  echo "RUNTIME_TYPE value is unknown: $RUNTIME_TYPE"
  exit 1

fi
