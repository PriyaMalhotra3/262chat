import asyncio

class ChatException(Exception):
    pass

class Session:
    def __init__(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
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
        self.username = username
        asyncio.create_task(self._consume())

    async def register(self, username, password):
        self._initiate("REGISTER", username, password)

    async def login(self, username, password):
        self._initiate("LOGIN", username, password)

    async def listen(self, event):
        return await self._queue(event).get()

    async def list_users(self):
        await self._send("LIST")
        return await response.listen("LISTING")

    async def delete(self):
        await self._send("DELETE")
        await self.listen("DELETED")

    async def message(self, to, text):
        await self._send(f"MESSAGE {to}\n{text}")
        await self.listen("SENT")
