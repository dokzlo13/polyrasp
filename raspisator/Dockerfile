FROM python:3.6-alpine

COPY ./raspisator/requirements.txt /bot/requirements.txt
WORKDIR /bot

# install requirements
RUN pip install -r requirements.txt

# install app
COPY ./raspisator /bot
COPY ./shared /bot/app/shared

# run the app server
ENTRYPOINT python run.py
