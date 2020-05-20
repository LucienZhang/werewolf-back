
# Werewolf Backend

[![996.icu](https://img.shields.io/badge/link-996.icu-red.svg?label=Anti%20996)](https://996.icu)
[![Repo size](https://img.shields.io/github/repo-size/LucienZhang/werewolf-back?label=Repo%20Size)](https://github.com/LucienZhang/werewolf-back)
[![Docker Image Version (latest by date)](https://img.shields.io/docker/v/lucienzhangzl/werewolf-back?label=Image%20Version)](https://hub.docker.com/r/lucienzhangzl/werewolf-back)
[![Docker Image Size (latest by date)](https://img.shields.io/docker/image-size/lucienzhangzl/werewolf-back?label=Image%20Size)](https://hub.docker.com/r/lucienzhangzl/werewolf-back)

## Status

[![Test Status](https://github.com/LucienZhang/werewolf-back/workflows/Test/badge.svg)](https://github.com/LucienZhang/werewolf-back/actions?query=workflow%3ATest)
[![Build status](https://github.com/LucienZhang/werewolf-back/workflows/Build/badge.svg)](https://github.com/LucienZhang/werewolf-back/actions?query=workflow%3ABuild)

## Introduction

This is an open source project for an online judge of game [*The Werewolves of Millers Hollow*](https://en.wikipedia.org/wiki/The_Werewolves_of_Millers_Hollow), this repo is the backend part, please find the frontend part [here](https://github.com/LucienZhang/werewolf-front).

To play this game, please visit [my game site](http://ziliang.red/werewolf/)

This project is implemented in [FastAPI](https://fastapi.tiangolo.com/) as a RESTful API, using WebSocket to send the status of game to the players in real time. [SQLAlchemy](https://www.sqlalchemy.org/) is used to manage the use of MySQL.

To deploy this project, you may need MySQL and Redis installed and configured beforehand. Moverover, you need to set some environmental variables or create a .env file under the root path.

```bash
SECRET_KEY = "YOU_SECRET_KEY"
SQLALCHEMY_DATABASE_URI = "mysql://username:password@hostname:port/database?charset=utf8"
REDIS_URL = "redis://you_redis_url"
BACKEND_CORS_ORIGINS = ["your CORS origins"]
```
