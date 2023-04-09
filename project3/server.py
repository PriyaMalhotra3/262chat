#/usr/bin/env python3

import os
import asyncio
import fnmatch
import sqlite3
import timezone
from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Callable

import grpc
from google.protobuf.empty_pb2 import Empty
from google.protobuf.timestamp_pb2 import Timestamp

from generated import replica_pb2, replica_pb2_grpc, chat_pb2, chat_pb2_grpc

@dataclass
class Message:
    from_: str
    to: str
    text: str
    sent: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

class Store:
    def __init__(filename: str):
        self.connection = sqlite3.connect(filename)
        self.cursor = self.connection.cursor()
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            name TEXT PRIMARY KEY,
            password TEXT
        ) STRICT
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages(
            from TEXT REFERENCES users(name),
            to   TEXT REFERENCES users(name),
            text TEXT NOT NULL,
            sent TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) STRICT
        """)

    def transcript(self):
        for from_, to, text, sent in self.cursor.execute("""
        SELECT from, to, text, sent FROM messages
        """):
            yield Message(from_, to, text, sent)

    def log(self, message: Message):
        self.cursor.execute(
            """
            INSERT INTO messages VALUES(?, ?, ?, ?)
            """,
            message.from_,
            message.to,
            message.text,
            message.sent
        )
        self.connection.commit()

    def user(self, name: str, password: str, delete: bool=False):
        if delete:
            pass
        else:
            self.cursor(
                """
                INSERT INTO users VALUES(?, ?)
                """,
                name,
                password
            )
        self.connection.commit()

T = TypeVar("T")
class Node(Generic[T]):
    def __init__(value: T,
                 nxt: Optional[Node[T]]=None,
                 prev: Optional[Node[T]]=None):
        self._value = value
        self.next = nxt
        self.prev = prev

    @property
    def value(self):
        return self._value

    def remove(self):
        if self.prev:
            self.prev.next = self.next

    def __iter__(self) -> Iterable[T]:
        current = self
        while current:
            yield current.value
            current = current.next

class Replica(replica_pb2_grpc.ReplicaServicer):
    def __init__(self,
                 cluster: Optional[str]=None,
                 database: LocalStore):
        super().__init__()

    @staticmethod
    def drain(to: Callable,
              iterator: AsyncIterable,
              cleanup: Callable[[], None]=lambda: pass):
        async def loop():
            try:
                async for payload in iterator:
                    to(payload)
            finally:
                cleanup()
        asyncio.create_task(loop())

    @staticmethod
    async def generator(queue: asyncio.Queue):
        while True:
            yield await queue.get()

    def connect(address: str):
        stub = chat_pb2_grpc.ChatStub(grpc.aio.insecure_channel(f"{host}:{port}"))

        self.firehoses = Node(asyncio.Queue(), self.firehoses)
        self.drain(
            self.firehose,
            stub.Firehose(self.generator(self.firehoses.value)),
            self.firehoses.remove
        )
        self.user_updates = Node(asyncio.Queue(), self.user_updates)
        self.drain(
            self.user_update,
            stub.UserUpdate(self.generator(self.user_updates.value)),
            self.user_updates.remove
        )

        return stub

    def log(self, message: replica_pb2.ReplicatedMessage):
        for q in self.firehoses:
            q.put_nowait(message)

    def user(self, update: chat_pb2.InitialRequest):
        for q in self.user_updates:
            q.put_nowait(update)

    async def Firehose(self, request, context):
        self.firehoses = Node(asyncio.Queue(), self.firehoses)
        self.drain(
            self.firehose,
            request,
            self.firehoses.remove
        )
        async for payload in generator(self.firehoses.value):
            yield payload

    async def UserUpdate(self, request, context):
        self.user_updates = Node(asyncio.Queue(), self.user_updates)
        self.drain(
            self.user_update,
            request,
            self.user_updates.remove
        )
        async for payload in generator(self.user_updates.value):
            yield payload

    async def Cluster(self, request, context):
        return replica_pb2.Peers(
            peers=self.peers
        )

@dataclass
class User:
    password: str
    queue: asyncio.Queue

class ReplicatedChat(chat_pb2_grpc.ChatServicer, replica_pb2_grpc.ReplicaServicer):
    def __init__(self,
                 database: Store,
                 cluster: Optional[str]=None):
        self.users = {}
        self.database = database
        self.peers: set[str] = set()
        self.firehoses = []
        self.user_updates = []
        stub = self.connect(cluster)
        for peer in (await stub.Cluster(Empty())).peers:
            self.connect(peer)
        self.Firehose = Bidirectional()
        self.UserUpdate = Bidirectional()

        class LiveStore(Store):
            def __init__(self, delegate: Store):
                self.delegate = delegate

            def transcript(self):
                return self.delegate.transcript()

            def user(self, name: str, password: str, delete: bool=False):
                return self.delegate.user(name, password, delete)

            def log(self, message: Message):
                # check if user is connected
                return self.delegate.log(message)
        self.store = LiveStore(database)
        self.replica = Replica(cluster, self.store)
        replica_pb2_grpc.add_ReplicaServicer_to_server(self.replica, replica)

        @staticmethod
    def drain(to: Callable,
              iterator: AsyncIterable,
              cleanup: Callable[[], None]=lambda: pass):
        async def loop():
            try:
                async for payload in iterator:
                    to(payload)
            finally:
                cleanup()
        asyncio.create_task(loop())

    @staticmethod
    async def generator(queue: asyncio.Queue):
        while True:
            yield await queue.get()

    def connect(address: str):
        stub = chat_pb2_grpc.ChatStub(grpc.aio.insecure_channel(f"{host}:{port}"))

        self.firehoses = Node(asyncio.Queue(), self.firehoses)
        self.drain(
            self.firehose,
            stub.Firehose(self.generator(self.firehoses.value)),
            self.firehoses.remove
        )
        self.user_updates = Node(asyncio.Queue(), self.user_updates)
        self.drain(
            self.user_update,
            stub.UserUpdate(self.generator(self.user_updates.value)),
            self.user_updates.remove
        )

        return stub

    def log(self, message: replica_pb2.ReplicatedMessage):
        for q in self.firehoses:
            q.put_nowait(message)

    def user(self, update: chat_pb2.InitialRequest):
        for q in self.user_updates:
            q.put_nowait(update)

    async def Firehose(self, request, context):
        self.firehoses = Node(asyncio.Queue(), self.firehoses)
        self.drain(
            self.firehose,
            request,
            self.firehoses.remove
        )
        async for payload in generator(self.firehoses.value):
            yield payload

    async def UserUpdate(self, request, context):
        self.user_updates = Node(asyncio.Queue(), self.user_updates)
        self.drain(
            self.user_update,
            request,
            self.user_updates.remove
        )
        async for payload in generator(self.user_updates.value):
            yield payload

    async def Cluster(self, request, context):
        return replica_pb2.Peers(
            peers=self.peers
        )

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
        if len(request.user.username.split(maxsplit=1)) != 1:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Username must not contain whitespace or be empty."
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
        while not context.cancelled():
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
        del self.users[request.username]
        return Empty()

    async def ListUsers(self, request, context):
        return chat_pb2.Users(
            usernames=fnmatch.filter(self.users.keys(), request.glob)
        )
        
async def serve(chat_port: int,
                replica_port: int,
                database: str,
                cluster: Optional[str]=None):
    chat = grpc.aio.server()
    replica = grpc.aio.server()
    servicer = ReplicatedChat(Store(database), cluster)
    replica_pb2_grpc.add_ReplicaServicer_to_server(servicer, replica)
    chat_pb2_grpc.add_ChatServicer_to_server(servicer, chat)
    replica.add_insecure_port(f"[::]:{replica_port}")
    chat.add_insecure_port(f"[::]:{chat_port}")
    await asyncio.gather(
        chat.start(),
        replica.start()
    )
    await asyncio.gather(
        chat.wait_for_termination()
        replica.wait_for_termination()
    )

if __name__ == '__main__':
    import sys
    from os import path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

    from ip import local_ip, parse_address
    import argparse
    parser = argparse.ArgumentParser(
        description="Replicated, persistent gRPC server for 262chat"
    )
    parser.add_argument("chat_port", type=int)
    parser.add_argument("replica_port", type=int)
    parser.add_argument("database", type=str)
    parser.add_argument("--cluster", type=parse_address)
    parser.add_argument("--self-destruct", type=int)
    
    port = int(os.getenv("PORT", 8080))
    print(f"Serving on {local_ip()}:{port}...")
    asyncio.run(serve(port))
