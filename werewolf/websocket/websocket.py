import asyncio
import logging
from fastapi import WebSocket, Depends
from starlette.concurrency import run_until_first_complete
from starlette.websockets import WebSocketDisconnect
from pydantic import ValidationError
from jose import jwt
from sqlalchemy.orm import Session
import json
from json import JSONDecodeError


from werewolf.core import security
from werewolf.core.config import settings
from .broadcaster import Broadcaster
from werewolf.models import User
from werewolf.api import deps
from werewolf.utils.enums import GameEnum
from werewolf.schemas.token import TokenPayload

broadcaster = Broadcaster(settings.REDIS_URL)


def init_websocket(app):

    # async def chatroom_ws_receiver(websocket):
    #     async for message in websocket.iter_text():
    #         await broadcaster.publish(channel="chatroom", message=message)

    async def info_ws_sender(websocket, channel):
        async with broadcaster.subscribe(channel=str(channel)) as subscriber:
            async for event in subscriber:
                await websocket.send_json(event.message, mode="binary")

    async def info_ws_heartbeat(websocket):
        try:
            while True:
                await asyncio.wait_for(websocket.receive_json(), settings.HEARTBEAT_TIMEOUT)
                logging.debug('heartbeat')
        except (asyncio.TimeoutError, WebSocketDisconnect, JSONDecodeError) as err:
            logging.debug(err)

    @app.websocket(settings.WEBSOCKET_URL)
    async def info_ws(
        websocket: WebSocket,
        token: str,
        db: Session = Depends(deps.get_db),
    ):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
            token_data = TokenPayload(**payload)
        except (jwt.JWTError, ValidationError):
            await websocket.close(code=GameEnum.CONNECTION_WS_4001_NOT_IN_GAME.label)
            return
        user = db.query(User).get(token_data.sub)
        if not user:
            await websocket.close(code=GameEnum.CONNECTION_WS_4001_NOT_IN_GAME.label)
            return

        if user.gid < 0:
            await websocket.close(code=GameEnum.CONNECTION_WS_4001_NOT_IN_GAME.label)
            return
        await websocket.accept()
        await run_until_first_complete(
            # (chatroom_ws_receiver, {"websocket": websocket}),
            (info_ws_heartbeat, {"websocket": websocket}),
            (info_ws_sender, {"websocket": websocket, "channel": user.gid}),
        )


def publish_info(channel, message):
    asyncio.run(broadcaster.publish(channel=channel, message=message))


def publish_history(channel, message, show=True):
    publish_info(channel, json.dumps({'history': message, 'show': show}))


def publish_music(channel, instruction, bgm, bgm_loop):
    publish_info(channel, json.dumps({'music': {'instruction': instruction, 'bgm': bgm, 'bgm_loop': bgm_loop}}))
