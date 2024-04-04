FROM python:3.11-alpine

RUN apk add sudo nmap iputils ffmpeg --no-cache && rm -f /var/cache/apk/*

COPY . /usr/src/app

WORKDIR /usr/src/app/src

RUN pip install --upgrade pip

RUN pip install pipenv

RUN pipenv lock && pipenv install --system --deploy

ENTRYPOINT ["/bin/bash", "-l", "-c"]