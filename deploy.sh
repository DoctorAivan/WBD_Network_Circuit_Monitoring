#!/bin/sh

# Action is the first param, it can be up or down. It must be set or script can't run
ACTION=$1
PROJECT="wbd_logs_tracking"
# wbd

# Run docker compose
if [ "$ACTION" = "up" ]; then
  docker-compose -f docker/docker-compose.yml -p $PROJECT up -d
elif [ "$ACTION" = "down" ]; then
  docker-compose -f docker/docker-compose.yml -p $PROJECT down
elif [ "$ACTION" = "nginx" ]; then
  docker-compose -f docker/docker-compose.yml restart nginx
else
  echo "Action must be \"up\" or \"down\""
  exit 1
fi