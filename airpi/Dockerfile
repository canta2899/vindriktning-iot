FROM alpine

RUN apk -U upgrade
RUN apk add --update --no-cache build-base
RUN apk add --update --no-cache libffi-dev openssl-dev
RUN apk add --update --no-cache sqlite
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN apk add py3-sqlalchemy
RUN pip3 install --no-cache --upgrade pip setuptools
RUN pip3 install --no-cache --upgrade flask
RUN pip3 install --no-cache --upgrade influxdb
RUN pip3 install --no-cache --upgrade flask_sqlalchemy
RUN pip3 install --no-cache --upgrade flask_jwt_extended
RUN pip3 install --no-cache --upgrade Flask-MQTT
RUN pip3 install --no-cache --upgrade passlib
RUN pip3 install --no-cache --upgrade gunicorn

RUN mkdir /app
RUN mkdir /log

WORKDIR /app

COPY ./app /app

