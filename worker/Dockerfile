FROM python:3.6-alpine

COPY ./worker/requirements.txt /queue/requirements.txt

WORKDIR /queue

# install required for LXML gcc-compiler
RUN apk add --update --no-cache g++ gcc libxslt-dev

#install requirements, CFLAGS for better compilation time
RUN CFLAGS="-O0" pip install -r requirements.txt

# install app
COPY ./worker /queue
COPY ./shared /worker/app/shared

ENTRYPOINT celery -A app worker -B --loglevel=INFO