from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from werewolf.api import api_router
# from werewolf.api.sio import sio_app
from werewolf.websocket.websocket import broadcaster, init_websocket
from werewolf.core.config import settings
from werewolf.utils.game_exceptions import GameFinished
from werewolf.utils.enums import GameEnum
from werewolf.websocket.websocket import publish_history
from werewolf.models import Game, Role

app = FastAPI()

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        # allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_PREFIX)
# app.mount(settings.WEB_SOCKET_PREFIX, sio_app)

init_websocket(app)


@app.on_event("startup")
async def startup_event():
    await broadcaster.connect()


@app.on_event("shutdown")
async def shutdown_event():
    await broadcaster.disconnect()


# @app.middleware("http")
# async def process(request: Request, call_next):
#     try:
#         response = await call_next(request)
#     except GameFinished as e:
#         try:
#             db = e.db
#             db.commit()
#             publish_history(e.gid, f'游戏结束，{e.winner.label}胜利')
#             game = db.query(Game).with_for_update().get(e.gid)
#             game.status = GameEnum.GAME_STATUS_FINISHED
#             original_players = game.players
#             game.init_game()
#             game.players = original_players
#             all_players = db.query(Role).filter(Role.gid == game.gid).all()
#             for p in all_players:
#                 p.reset()
#             db.commit()
#         except SQLAlchemyError:
#             db.rollback()
#             raise
#         finally:
#             db.close()
#             return GameEnum.OK.digest()
#     return response

@app.exception_handler(GameFinished)
async def game_finished_handler(request: Request, finish: GameFinished):
    try:
        db = finish.db
        db.commit()
        publish_history(finish.gid, f'游戏结束，{finish.winner.label}胜利')
        game = db.query(Game).with_for_update().get(finish.gid)
        game.status = GameEnum.GAME_STATUS_FINISHED
        original_players = game.players
        game.init_game()
        game.players = original_players
        all_players = db.query(Role).filter(Role.gid == game.gid).all()
        for p in all_players:
            p.reset()
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.rollback()
        db.close()
    return GameEnum.OK.digest()


###
# test
###

# from starlette.templating import Jinja2Templates
# templates = Jinja2Templates("templates")


# @app.get("/test")
# async def test(request: Request):
#     template = "index.html"
#     context = {"request": request}
#     return templates.TemplateResponse(template, context)


# @app.get("/send/{gid}/{msg}")
# async def send(msg: str, gid: str):
#     import json
#     message = json.dumps({"action": 'message', "user": "god", "message": msg})
#     await broadcaster.publish(channel=gid, message=message)

# from werewolf.api.deps import get_current_active_user
# from fastapi import Depends
# from werewolf.models import User
# @app.get("/users/me")
# async def read_items(current_user: User = Depends(get_current_active_user)):
#     return {"gid": current_user.gid}
