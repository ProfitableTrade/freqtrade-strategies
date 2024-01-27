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

function start_docker_compose {

  echo "" > ./trade.env
  echo "export DOMAIN=$DOMAIN" >> ./trade.env
  echo "export TRADE_NAME=$TRADE_NAME" >> ./trade.env
  echo "export ENV_NAME=$ENV_NAME" >> ./trade.env
  echo "export STRATEGY=$STRATEGY" >> ./trade.env
  echo "export CONFIG_NAME=$CONFIG_NAME" >> ./trade.env
  echo "export DRY_RUN_WALLET=$DRY_RUN_WALLET" >> ./trade.env
  echo "export RUNTIME_TYPE=$RUNTIME_TYPE" >> ./trade.env
  chmod 777 ./trade.env

  docker compose -f docker-compose-trade.yml up -d
}

start_docker_compose \
  && echo "--------------------------------------------------------------------" \
  && docker logs ${ENV_NAME}-freqtrade \
  && echo "--------------------------------------------------------------------" \
  && sleep 5 \
  && docker logs ${ENV_NAME}-freqtrade --since 5s \
  && echo "--------------------------------------------------------------------" \
  && sleep 5 \
  && docker logs ${ENV_NAME}-freqtrade --since 5s \
  && echo "--------------------------------------------------------------------" \
  && sleep 5 \
  && docker logs ${ENV_NAME}-freqtrade --since 5s \
  && echo "--------------------------------------------------------------------"
