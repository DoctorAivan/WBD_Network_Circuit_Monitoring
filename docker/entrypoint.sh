#!/bin/sh
if [ "$PRODUCTION" = "1" ]; then
  gunicorn -w 8 \
      -k gevent \
      --worker-connections 1000 \
      --bind :8000 \
      core.wsgi:application

elif [ "$PRODUCTION" = "0" ]; then
  python manage.py runserver 0.0.0.0:8000
fi