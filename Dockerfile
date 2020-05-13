FROM ubuntu:latest

COPY app /opt/app
COPY entrypoint.sh /opt/entrypoint.sh

WORKDIR /opt/app

ENV LANG=C.UTF-8 \ 
    LC_ALL=C.UTF-8

ENTRYPOINT  ["/opt/entrypoint.sh"]
