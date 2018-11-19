FROM python:3.6.7-slim-jessie

RUN apt-get clean && apt-get update && apt-get install -y locales
RUN sed -i -e 's/# ru_RU.UTF-8 UTF-8/ru_RU.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen

ENV LANG='ru_RU.UTF-8' LANGUAGE='ru_RU:ru' LC_ALL='ru_RU.UTF-8'

COPY ./raspisator/requirements.txt /bot/requirements.txt
WORKDIR /bot

# install requirements
RUN pip install -r requirements.txt

# install app
COPY ./raspisator /bot
COPY ./shared /bot/app/shared

# run the app server
ENTRYPOINT python run.py
