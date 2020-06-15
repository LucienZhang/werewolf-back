FROM python:3.7-slim-buster
WORKDIR /data/project
ENV DEBIAN_FRONTEND noninteractive
ENV DEBCONF_NOWARNINGS yes
ENV PYTHONIOENCODING utf-8
ENV LANG C.UTF-8

COPY . .
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-libmysqlclient-dev gcc && \
    pip install -r requirements.txt
CMD [ "gunicorn", "werewolf:app", "-c", "./gunicorn.conf.py" ]
