FROM python:3.6-alpine

COPY ./requirements.txt /queue/requirements.txt

WORKDIR /queue

# install required for LXML gcc-compiler
RUN apk add --update --no-cache g++ gcc libxslt-dev

#install requirements, CFLAGS for better compilation time
RUN CFLAGS="-O0" pip install -r requirements.txt

# install app
COPY ./app /queue

ENTRYPOINT celery -A deferred worker -B --loglevel=INFO