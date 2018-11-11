FROM python:3.6-alpine

COPY ./requirements.txt /bot/requirements.txt
WORKDIR /bot

# install requirements
RUN pip install -r requirements.txt

# install app
COPY ./app /bot

# run the app server
ENTRYPOINT python run.py
