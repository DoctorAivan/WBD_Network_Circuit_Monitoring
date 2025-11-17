#FROM python:3.13-alpine
FROM arm64v8/python:3.13-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY ./requirements.txt .

#RUN pip install -r requirements.txt && pip install gunicorn gevent
RUN apt-get update && apt-get install -yy build-essential gcc && pip install --upgrade pip && pip install -r requirements.txt && pip install gunicorn gevent

EXPOSE 8000

# Run migrations and server at entrypoint
ENTRYPOINT ./docker/entrypoint.sh
