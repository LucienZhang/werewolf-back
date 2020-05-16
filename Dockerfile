FROM python:3.7
WORKDIR /data/project
ENV PYTHONIOENCODING utf-8
ENV LANG en_US.UTF-8

COPY . .
VOLUME [ "/data/project/werewolf/instance" ]
RUN pip install --upgrade pip && \
    pip install -r requirements.txt
CMD [ "gunicorn", "werewolf:create_app()", "-c", "./werewolf/instance/gunicorn.conf.py" ]
