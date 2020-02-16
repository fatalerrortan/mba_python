FROM ubuntu:latest

COPY app /opt/app
COPY entrypoint.sh /opt/entrypoint.sh

WORKDIR /opt/app

ENV LANG=C.UTF-8 \ 
    LC_ALL=C.UTF-8

RUN apt update && \
    apt -y dist-upgrade && \
    # install python environment
    apt install -y python3 && \
    apt install -y python3-pip && \
    pip3 install -r requirements.txt && \
    # install redis server
    apt install -y redis-server

ENTRYPOINT  ["/opt/entrypoint.sh"]
