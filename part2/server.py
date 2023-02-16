import os
import asyncio
from datetime import datetime, timezone
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

    def _validate(self, user, context):
        if request.user.username not in self.users:
            context.set_details("Incorrect username.")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return False
        if request.user.password != self.users[request.user.username].password:
            context.set_details("Incorrect username.")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return False
        return True

    async def Initiate(self, request, context):
        if request.create:
            if request.user.username in self.users:
                context.set_details(f"Username {request.user.username} is not available.")
                context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                return
            self.users[request.user.username] = User(request.user.password, asyncio.Queue())
        if not self._validate(request.user, context):
            return
        while True:
            yield await self.users[request.user.username].queue.get()

    async def SendMessage(self, request, context):
        if not self._validate(request.user, context):
            return Empty()
        if request.message.username not in self.users:
            context.set_details(f"{request.message.username} is not a user; try ListUsers to see available users.")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        message = request.message
        message.username = request.user.username
        sent = Timestamp()
        sent.FromDatetime(datetime.now(timezone.utc))
        await self.users[request.message.username].queue.put(chat_pb2.ReceivedMessage(
            message=message,
            sent=sent
        ))
        return Empty()

    async def DeleteAccount(self, request, context):
        if not self._validate(request, context):
            return Empty()
        del self.users[request.user.username]
        return Empty()

    async def ListUsers(self, request, context):
        return chat_pb2.Accounts(
            usernames=fnmatch.filter(users.keys(), request.pattern)
        )
        
async def serve(port):
    server = grpc.aio.server()
    chat_pb2_grpc.add_ChatServicer_to_server(Chat(), server)
    server.add_insecure_port(f"[::]:{port}")
    print(f"Serving on localhost:{port}...")
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    asyncio.run(serve(int(os.getenv("PORT", 8080))))
