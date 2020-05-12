import asyncio
import logging
import typing
from fastapi import WebSocket, Depends
# from starlette.concurrency import run_until_first_complete
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


async def run_until_first_complete(*args: typing.Tuple[typing.Callable, dict]) -> None:
    tasks = [asyncio.create_task(handler(**kwargs)) for handler, kwargs in args]
    (done, pending) = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    logging.debug('first finished')
    logging.debug('done', done)
    logging.debug('pending', pending)
    [task.cancel() for task in pending]
    [task.result() for task in done]
    logging.debug('task done!')


async def info_ws_sender(websocket, channel):
    try:
        async with broadcaster.subscribe(channel=str(channel)) as subscriber:
            async for event in subscriber:
                await websocket.send_text(event.message)
            logging.debug('Finishing sender')
    except asyncio.CancelledError:
        logging.log(f'sender with channel={channel} canceled')
        raise


async def info_ws_heartbeat(websocket):
    try:
        while True:
            await asyncio.wait_for(websocket.receive_json(), settings.HEARTBEAT_TIMEOUT)
            logging.debug('heartbeat')
    except (asyncio.TimeoutError, WebSocketDisconnect, JSONDecodeError) as err:
        logging.debug('Finishing heartbeat', err)


def init_websocket(app):

    # async def chatroom_ws_receiver(websocket):
    #     async for message in websocket.iter_text():
    #         await broadcaster.publish(channel="chatroom", message=message)

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
    asyncio.create_task(broadcaster.publish(channel=channel, message=message))


def publish_history(channel, message, show=True):
    publish_info(channel, json.dumps({
        'history': message,
        'show': show,
        'mutation': 'SOCKET_HISTORY'
    }))


def publish_music(channel, instruction, bgm, bgm_loop):
    publish_info(channel, json.dumps({
        'instruction': instruction,
        'bgm': bgm,
        'bgm_loop': bgm_loop,
        'mutation': 'SOCKET_AUDIO'
    }))
