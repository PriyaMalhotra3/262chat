import asyncio

class ChatException(Exception):
    pass

class Session:
    def __init__(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self._reader = reader
        self._writer = writer
        self.logged_in = False
        self._news = asyncio.Condition()

    @classmethod
    async def connect(cls, host, port):
        reader, writer = await asyncio.open_connection(host, port)
        return cls(reader, writer)

    async def _send(self, s):
        self._writer.write(s.encode("utf-8") + b"\0")
        await self._writer.drain()

    async def _read(self):
        transfer_buffer = await self._reader.readuntil(b"\0")
        parsed = transfer_buffer[:-1].decode("utf-8").split(maxsplit=1)
        if parsed[0] == "ERROR":
            raise ChatException(parsed[1])
        return parsed

    async def _consume(self):
        while True:
            latest = await self._read()
            async with self._news:
                self._latest = latest
                self._news.notify_all()

    async def _initiate(self, command, username, password):
        await self._send(f"{command.upper()} {username}\0{password}")
        await self._read()
        self.logged_in = true
        self.username = username
        asyncio.create_task(self._consume())

    async def register(self, username, password):
        self._initiate("REGISTER", username, password)

    async def login(self, username, password):
        self._initiate("LOGIN", username, password)

    async def listen(self, *events):
        async with self._news:
            await self._news.wait_for(
                lambda: any(self._latest[0] == event.upper()
                            for event in events)
            )
            return self._latest

    async def list_users(self):
        await self._send("LIST")
        return await response.listen("LISTING")

    async def delete(self):
        await self._send("DELETE")
        await self.listen("DELETED")

    async def message(self, to, text):
        await self._send(f"MESSAGE {to}\n{text}")
        await self.listen("SENT")
