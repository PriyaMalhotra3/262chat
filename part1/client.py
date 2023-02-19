import re
import asyncio
from datetime import datetime

from interface import Message, AbstractSession

class ChatException(Exception):
    pass

class Session(AbstractSession):
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self._reader = reader
        self._writer = writer
        self._queues = {}

    @classmethod
    async def connect(cls, host, port):
        reader, writer = await asyncio.open_connection(host, port)
        return cls(reader, writer)

    async def _send(self, s):
        self._writer.write(s.encode("utf-8") + b"\0")
        await self._writer.drain()

    async def _receive(self):
        transfer_buffer = await self._reader.readuntil(b"\0")
        parsed = transfer_buffer[:-1].decode("utf-8").split(maxsplit=1)
        if parsed[0] == "ERROR":
            raise ChatException(parsed[1])
        return parsed

    def _queue(self, name):
        return self._queues.setdefault(name, asyncio.Queue())

    async def _consume(self):
        while True:
            payload = await self._receive()
            await self._queue(payload[0]).put(payload)

    async def _initiate(self, command, username, password):
        await self._send(f"{command.upper()} {username}\0{password}")
        await self._receive()
        self._username = username
        asyncio.create_task(self._consume())

    @property
    def username(self):
        return self._username

    async def register(self, username, password):
        await self._initiate("REGISTER", username, password)

    async def login(self, username, password):
        await self._initiate("LOGIN", username, password)

    async def _listen(self, event):
        return await self._queue(event).get()

    async def list_users(self, pattern="*"):
        await self._send(f"LIST {pattern}")
        users = await self._listen("LISTING")
        return users[1].split("\n") if len(users) > 1 else []

    async def delete(self):
        await self._send("DELETE")
        await self._listen("DELETED")

    async def message(self, payload: Message):
        await self._send(f"MESSAGE {payload.to}\n{payload.text}")
        await self._listen("SENT")

    async def stream(self):
        while True:
            _, raw = await self._listen("MESSAGE")
            to, _, sent, text = re.split(r"[\s\0]+", raw, maxsplit=3)
            yield Message(
                to=to,
                text=text,
                sent=datetime.fromisoformat(sent)
            )

    async def close(self):
        await self.writer.wait_closed()
