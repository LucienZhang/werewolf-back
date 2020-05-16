FROM python:3.7
WORKDIR /data/project
ENV PYTHONIOENCODING utf-8
ENV LANG en_US.UTF-8

COPY . .
VOLUME [ "/data/project/gunicorn.conf.py" ]
VOLUME [ "/data/project/.env" ]
RUN pip install --upgrade pip && \
    pip install -r requirements.txt
CMD [ "gunicorn", "werewolf:app", "-c", "./gunicorn.conf.py" ]
