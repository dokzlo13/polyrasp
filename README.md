Политех.Расписание
==================
[![image](https://img.shields.io/myget/mongodb/v/MongoDB.Driver.Core.svg)](https://github.com/docker-library/mongo/blob/6932ac255d29759af9a74c6931faeb02de0fe53e/4.0/Dockerfile) [![image](https://img.shields.io/badge/python-3.6-green.svg)](https://github.com/docker-library/python/blob/39c500cc8aefcb67a76d518d789441ef85fc771f/3.6/stretch/slim/Dockerfile) [![image](https://img.shields.io/badge/redis-5.0.1-green.svg)](https://github.com/docker-library/redis/blob/a5d019077b46494751482512c200c4df34463dc6/5.0/Dockerfile) [![Build Status](https://travis-ci.com/dokzlo13/polyrasp.svg?branch=master)](https://travis-ci.com/dokzlo13/polyrasp)

#### Используемый технологический стек:
---------
- Python 3.6 /  [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) / [requests](https://github.com/requests/requests) / [Jinja2](https://github.com/pallets/jinja) / [lxml](https://lxml.de/)
- Celery
- Redis
- Mongodb
- Docker
Информация о расписаниях предоставляется ресурсом **[ruz.spbstu.ru](http://ruz.spbstu.ru/)**

Проект состоит из двух частей - воркера **Celery** ([worker](../master/worker)) и непосредственно **Telegram-бота** ([raspisator](../master/raspisator)), а так же общих исходников ([shared](../master/shared))
Бот авторизует пользователей по их Telegram-user-id и использует механизм подписок. Для каждого пользователя может быть создан список подписок, включающий определенные учебные группы. Пользователь получает информацию, которая хранится в  БД, во избежание продолжительного ожидание ответов от ruz.spbstu.ru.
Для каждой подписки задача Celery обновляет расписание через фиксированные промежутки времени. Расписание обновляется на фиксированную "глубину" - **две недели** от текущей даты. Инициализация новой подписки происходи с "глубиной" в **10 недель**. Расписание обновляется через запросы к ресурсу **ruz.spbstu.ru**. Информация извлекается из тела страницы, и, в часности, переменной **"window._\_INITIAL_STATE_\_"**, которая содержит json-данные. Данные после обработки хранятся в виде документов в MongoDB.
Celery так же используется для поиска информации о занятиях преподавателей и информации о структуре институтов и специальностей.
Так же Celery используется для удаления подписок, которые не используются ни одним из пользователей. 
Redis используется как кеш для состояний поиска.

#### Установка
---------
Для сборки проекта необходимо выполнить:
```bash
$ git clone https://github.com/dokzlo13/polyrasp.git
$ cd ./polyrasp
$ docker-compose build
```
Для запуска бота необходимо указать токен, это можно сделать с помощью переменной окружения **BOT_TOKEN**
Переменную можно указать как в файле **_variables.env_**, так и непосредственно перед запуском
```bash
$ BOT_TOKEN=123456789:IqpqbmjcxrLLHnHlMWBfSStfZUurxsCDnZI DEBUG=1 docker-compose up 
```

#### Локальный запуск
---------
Так как компоненты системы требуют общие исходники для работы, в каталогах **app** ([worker/app](../master/worker/app), [raspisator/app](../master/raspisator/app)) должен быть размещен пакет shared.

Для локального запуска необходимо использовать следующие команды:
**Для бота:**
```bash
cd ./raspisator
rm -rf ./app/shared && cp -r ../shared/ ./app/shared && BOT_TOKEN=TOKEN DEBUG=1 python3 run.py
```
**Для воркера:**
```bash
cd ./worker
rm -rf ./app/shared && cp -r ../shared/ ./app/shared && celery -A app worker -B
```
Redis и MongoDB могут быть запущены отдельно в контейнере
```bash
docker-compose up redis mongo
```

