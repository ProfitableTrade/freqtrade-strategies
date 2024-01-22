#!/usr/bin/env bash

set -e

if [[ ! -f ./trade.env ]]; then

  echo "trade.env is not found"

else

  source ./trade.env

  export DOMAIN=${DOMAIN}
  export TRADE_NAME=${TRADE_NAME}
  export ENV_NAME=${ENV_NAME}
  export STRATEGY=${STRATEGY}
  export CONFIG_NAME=${CONFIG_NAME}
  export DRY_RUN_WALLET=${DRY_RUN_WALLET}
  export RUNTIME_TYPE=${RUNTIME_TYPE}

  export CONTAINER_NAME=${TRADE_NAME}-freqtrade

  if [[ "$(docker ps -a -q -f name=$CONTAINER_NAME)" != "" ]]; then
    echo "stop container"
    docker stop $CONTAINER_NAME
  else
    echo "The container $CONTAINER_NAME is not working"
  fi

fi
