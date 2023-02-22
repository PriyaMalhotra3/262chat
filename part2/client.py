import sys
import os
import logging

import grpc

from interface import Message, AbstractSession
from .generated import chat_pb2, chat_pb2_grpc

class Session(AbstractSession):
    def __init__(self, channel):
        self.channel = channel
        self.stub = chat_pb2_grpc.ChatStub(channel)

    @classmethod
    async def connect(cls, host, port):
        return cls(grpc.aio.insecure_channel(f"{host}:{port}"))

    async def _initiate(self, create, username, password):
        self.auth = chat_pb2.Authentication(
            username=username,
            password=password
        )
        self._stream = self.stub.Initiate(chat_pb2.InitialRequest(
            create=create,
            user=self.auth
        ))
        await self._stream.read()

    @property
    def username(self):
        return self.auth.username

    async def register(self, username, password):
        await self._initiate(True, username, password)

    async def login(self, username, password):
        await self._initiate(False, username, password)

    async def list_users(self, pattern="*"):
        return (await self.stub.ListUsers(chat_pb2.Filter(glob=pattern))).usernames

    async def delete(self):
        await self.stub.DeleteAccount(self.auth)

    async def message(self, message: Message):
        await self.stub.SendMessage(chat_pb2.SentMessage(
            message=chat_pb2.Message(
                username=message.to,
                text=message.text
            ),
            user=self.auth
        ))

    async def stream(self):
        while True:
            message = await self._stream.read()
            yield Message(
                to=message.message.username,
                text=message.message.text,
                sent=message.sent.ToDatetime()
            )

    async def close(self):
        self._stream.cancel()
        await self.channel.close()
