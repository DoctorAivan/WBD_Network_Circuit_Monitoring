#!/bin/sh

docker exec -it $1 $2

# ./cmd_docker.sh wbd_logs_tracking_backend "python manage.py makemigrations"
# ./cmd_docker.sh wbd_logs_tracking_backend "python manage.py migrate"