FROM python:3.7-slim-buster
WORKDIR /data/project
ENV PYTHONIOENCODING utf-8
ENV LANG en_US.UTF-8

COPY . .
RUN apt update && \
    apt install libmysqlclient-dev && \
    pip install --upgrade pip && \
    pip install -r requirements.txt
CMD [ "gunicorn", "werewolf:app", "-c", "./gunicorn.conf.py" ]
