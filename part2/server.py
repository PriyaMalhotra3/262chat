import os
import asyncio
import fnmatch
from datetime import datetime
from dataclasses import dataclass

import grpc
from google.protobuf.empty_pb2 import Empty
from google.protobuf.timestamp_pb2 import Timestamp

from generated import chat_pb2, chat_pb2_grpc

@dataclass
class User:
    password: str
    queue: asyncio.Queue

class Chat(chat_pb2_grpc.ChatServicer):
    def __init__(self):
        super().__init__()
        self.users = {}

    async def _validate(self, user, context):
        if user.username not in self.users:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Incorrect username."
            )
        if user.password != self.users[user.username].password:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Incorrect password."
            )

    async def Initiate(self, request, context):
        if not request.user.username.strip():
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Username must not be empty."
            )
        if request.create:
            if request.user.username in self.users:
                await context.abort(
                    grpc.StatusCode.ALREADY_EXISTS,
                    f"Username {request.user.username} is not available."
                )
            self.users[request.user.username] = User(request.user.password, asyncio.Queue())
        await self._validate(request.user, context)
        yield chat_pb2.ReceivedMessage() # Heartbeat message.
        while True:
            yield await self.users[request.user.username].queue.get()

    async def SendMessage(self, request, context):
        await self._validate(request.user, context)
        if request.message.username not in self.users:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                f"{request.message.username} is not a user; try ListUsers to see available users."
            )
        to = request.message.username
        message = request.message
        message.username = request.user.username
        sent = Timestamp()
        sent.FromDatetime(datetime.now())
        await self.users[to].queue.put(chat_pb2.ReceivedMessage(
            message=message,
            sent=sent
        ))
        return Empty()

    async def DeleteAccount(self, request, context):
        await self._validate(request, context)
        del self.users[request.user.username]
        return Empty()

    async def ListUsers(self, request, context):
        return chat_pb2.Users(
            usernames=fnmatch.filter(self.users.keys(), request.glob)
        )
        
async def serve(port):
    server = grpc.aio.server()
    chat_pb2_grpc.add_ChatServicer_to_server(Chat(), server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    import sys
    from os import path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
    from ip import local_ip
    port = int(os.getenv("PORT", 8080))
    print(f"Serving on {local_ip()}:{port}...")
    asyncio.run(serve(port))
