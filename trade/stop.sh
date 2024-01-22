#!/usr/bin/env bash

set -e

source ./trade.env

export DOMAIN=${DOMAIN}
export TRADE_NAME=${TRADE_NAME}
export ENV_NAME=${ENV_NAME}
export STRATEGY=${STRATEGY}
export CONFIG_NAME=${CONFIG_NAME}
export DRY_RUN_WALLET=${DRY_RUN_WALLET}
export RUNTIME_TYPE=${RUNTIME_TYPE}

function stop_docker_compose {
  docker compose -f docker-compose-trade.yml down
}

stop_docker_compose \
  && echo "--------------------------------------------------------------------" \
  && docker logs ${ENV_NAME}-freqtrade \
  && echo "--------------------------------------------------------------------"
