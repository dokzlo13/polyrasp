FROM python:3.6-alpine


RUN apk --no-cache add ca-certificates wget && \
    wget -q -O /etc/apk/keys/sgerrand.rsa.pub https://alpine-pkgs.sgerrand.com/sgerrand.rsa.pub && \
    wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.25-r0/glibc-2.25-r0.apk && \
    wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.25-r0/glibc-bin-2.25-r0.apk && \
    wget https://github.com/sgerrand/alpine-pkg-glibc/releases/download/2.25-r0/glibc-i18n-2.25-r0.apk && \
    apk add glibc-bin-2.25-r0.apk glibc-i18n-2.25-r0.apk glibc-2.25-r0.apk

# Iterate through all locale and install it
# Note that locale -a is not available in alpine linux, use `/usr/glibc-compat/bin/locale -a` instead
RUN /usr/glibc-compat/bin/localedef -i ru_RU -f UTF-8 ru_RU.UTF-8
#/usr/glibc-compat/bin/localedef -i en_US -f UTF-8 en_US.UTF-8 &&

# Set the lang, you can also specify it as as environment variable through docker-compose.yml
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
