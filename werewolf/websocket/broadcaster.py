import asyncio
import asyncio_redis
import typing
from contextlib import asynccontextmanager
from urllib.parse import urlparse
import logging


class Event:
    def __init__(self, channel, message):
        self.channel = channel
        self.message = message

    def __eq__(self, other):
        return (
            isinstance(other, Event) and self.channel == other.channel and self.message == other.message
        )

    def __repr__(self):
        return f'Event(channel={self.channel!r}, message={self.message!r})'


class RedisBackend(object):
    def __init__(self, url: str):
        parsed_url = urlparse(url)
        self._host = parsed_url.hostname or "localhost"
        self._port = parsed_url.port or 6379

    async def connect(self) -> None:
        self._pub_conn = await asyncio_redis.Connection.create(self._host, self._port)
        self._sub_conn = await asyncio_redis.Connection.create(self._host, self._port)
        self._subscriber = await self._sub_conn.start_subscribe()

    async def disconnect(self) -> None:
        self._pub_conn.close()
        self._sub_conn.close()

    async def subscribe(self, channel: str) -> None:
        await self._subscriber.subscribe([channel])

    async def unsubscribe(self, channel: str) -> None:
        await self._subscriber.unsubscribe([channel])

    async def publish(self, channel: str, message: typing.Any) -> None:
        await self._pub_conn.publish(channel, message)

    async def next_published(self) -> Event:
        message = await self._subscriber.next_published()
        return Event(channel=message.channel, message=message.value)


class Unsubscribed(Exception):
    pass


class Broadcaster:
    def __init__(self, url: str):
        self._subscribers = {}
        self._backend = RedisBackend(url)

    async def __aenter__(self) -> 'Broadcaster':
        await self.connect()
        return self

    async def __aexit__(self, *args, **kwargs) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        await self._backend.connect()
        self._listener_task = asyncio.create_task(self._listener())

    async def disconnect(self) -> None:
        if self._listener_task.done():
            self._listener_task.result()
        else:
            self._listener_task.cancel()
        await self._backend.disconnect()

    async def _listener(self) -> None:
        while True:
            event = await self._backend.next_published()
            for queue in list(self._subscribers.get(event.channel, [])):
                await queue.put(event)

    async def publish(self, channel: str, message: typing.Any) -> None:
        await self._backend.publish(channel, message)

    @asynccontextmanager
    async def subscribe(self, channel: str) -> 'Subscriber':
        queue: asyncio.Queue = asyncio.Queue()

        try:
            if not self._subscribers.get(channel):
                await self._backend.subscribe(channel)
                self._subscribers[channel] = set([queue])
            else:
                self._subscribers[channel].add(queue)
            logging.info(f'Start subscribe channel:{channel}')
            yield Subscriber(queue)
            logging.info(f'Finish subscribe channel:{channel}')
            self._subscribers[channel].remove(queue)
            if not self._subscribers.get(channel):
                del self._subscribers[channel]
                await self._backend.unsubscribe(channel)
        finally:
            await queue.put(None)


class Subscriber:
    def __init__(self, queue):
        self._queue = queue

    async def __aiter__(self):
        try:
            while True:
                yield await self.get()
        except Unsubscribed:
            pass

    async def get(self) -> Event:
        item = await self._queue.get()
        if item is None:
            raise Unsubscribed()
        return item
