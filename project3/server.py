#/usr/bin/env python3

import sys
import asyncio
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass, field
from contextlib import contextmanager
from typing import Optional, Callable, Union, Awaitable, Generic, TypeVar, Iterable, Any

import grpc
from google.protobuf.empty_pb2 import Empty
from google.protobuf.timestamp_pb2 import Timestamp

from generated import replica_pb2, replica_pb2_grpc, chat_pb2, chat_pb2_grpc

sqlite3.register_adapter(Timestamp, lambda timestamp: timestamp.ToJsonString())

T = TypeVar("T")
class Node(Generic[T]):
    def __init__(self,
                 value: T,
                 next_: "LinkedList[T]"=None,
                 prev: "LinkedList[T]"=None):
        self._value = value
        self.next = next_
        if self.next:
            self.next.prev = self
        self.prev = prev
        if self.prev:
            self.prev.next = self

    @property
    def value(self) -> T:
        return self._value

    def remove(self):
        if self.prev:
            self.prev.next = self.next
        if self.next:
            self.next.prev = self.prev

    def __iter__(self) -> Iterable[T]:
        current: "LinkedList[T]" = self
        while current:
            yield current.value
            current = current.next

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.remove()
        return False
LinkedList = Optional[Node[T]]

class ReplicatedChat(chat_pb2_grpc.ChatServicer, replica_pb2_grpc.ReplicaServicer):
    def __init__(self,
                 database: str,
                 cluster: Optional[str]=None):
        self.cluster = cluster
        self.database = database
        self.peers: set[str] = set()
        self.firehoses:    LinkedList[asyncio.Queue[replica_pb2.ReplicatedMessage]] = None
        self.user_updates: LinkedList[asyncio.Queue[chat_pb2.InitialRequest]]       = None
        self.clients: dict[str, asyncio.Queue[chat_pb2.ReceivedMessage]] = {}

    async def __aenter__(self):
        self.connection = sqlite3.connect(self.database)
        self.cursor = self.connection.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON")
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
            name TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages(
            'from' TEXT REFERENCES users(name),
            'to'   TEXT REFERENCES users(name),
            text TEXT NOT NULL,
            sent DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            UNIQUE ('from', 'to', sent)
        )
        """)
        # Tell SQLite3 that we will be sorting the "sent" column of messages often, so it should a lookup table ordering "sent" in ascending order:
        self.cursor.execute("""
        CREATE INDEX IF NOT EXISTS timestamps
        ON messages (sent ASC)
        """)

        if self.cluster and self.cluster not in self.peers:
            stub = replica_pb2_grpc.ReplicaStub(grpc.aio.insecure_channel(self.cluster))
            for peer in (await stub.Cluster(Empty())).peers:
                self.connect(peer)
            self.connect(self.cluster, stub)

        return self

    async def __aexit__(self, *exc):
        """Closes the database connection properly."""
        self.connection.close()
        return False

    ### Peer-side:

    async def Cluster(self, request, context):
        """Reports addresses of known peers in this cluster."""
        return replica_pb2.Peers(
            peers=self.peers
        )

    def message(self, from_: str, to: str, text: str, sent=None):
        """Adds a message to the local database and delivers it if the recipient is connected to this server."""
        sent = self.cursor.execute(
            "INSERT INTO messages('from', 'to', text"
            + (", sent" if sent is not None else "")
            + ") VALUES(?, ?, ?"
            + (", ?" if sent is not None else "")
            + ") RETURNING sent",
            (from_, to, text, sent)
            if sent is not None
            else (from_, to, text)
        ).fetchone()[0]
        self.connection.commit()
        time = Timestamp()
        time.FromJsonString(sent)
        try:
            self.clients[to].put_nowait(chat_pb2.ReceivedMessage(
                message=chat_pb2.Message(
                    username=from_,
                    text=text
                ),
                sent=time
            ))
        except KeyError:
            # Recipient must be on different server or offline and will get message from transcript on logon.
            pass
        return sent

    def save(self, message: replica_pb2.ReplicatedMessage):
        """Saves a ReplicatedMessage to the database."""
        self.message(
            getattr(message, "from"),
            message.message.username,
            message.message.text,
            message.sent
        )

    def update_user(self, update: chat_pb2.InitialRequest):
        """Performs the update to the users table requested by the InitialRequest."""
        if update.create:
            self.cursor.execute(
                "INSERT INTO users(name, password) VALUES(?, ?)",
                (update.user.name, update.user.password)
            )
        else:
            self.cursor.execute(
                "DELETE FROM messages WHERE from=? OR to=?",
                (update.user.username, update.user.username)
            )
            self.cursor.execute(
                "DELETE FROM users WHERE name=?",
                update.user.username
            )
        self.connection.commit()

    @staticmethod
    def notify(subscribers: LinkedList[asyncio.Queue], payload):
        """Notifies all subscribers of the new payload."""
        if not subscribers:
            return
        for queue in subscribers:
            queue.put_nowait(payload)

    @contextmanager
    def peer(self, address: str):
        """Keeps peer in the known-peers list as long as the connection is unbroken."""
        if address not in self.peers:
            print("Replica connected: " + address)
        self.peers.add(address)
        try:
            yield address
        except grpc.aio.AioRpcError as e:
            print(e)
        finally:
            try:
                self.peers.remove(address)
                print("Replica disconnected: " + address)
            except KeyError:
                # Peer already disconnected.
                pass

    def join(self,
             peer: str,
             destination: Callable,
             incoming: Union["RequestType", grpc.aio.StreamStreamMultiCallable],
             outgoing: Node[asyncio.Queue],
             until: Callable[[], Any]=lambda: False):
        """Connects two bidirectional streams in a pub-sub topology."""
        async def forward(outgoing):
            with self.peer(peer), outgoing:
                while not until():
                    yield await outgoing.value.get()
        async def backward(incoming):
            with self.peer(peer), outgoing:
                async for payload in incoming:
                    try:
                        destination(payload)
                    except sqlite3.IntegrityError:
                        # UNIQUE constraint violated, we must have already received the message.
                        pass

        isrpc = isinstance(incoming, grpc.aio.StreamStreamMultiCallable)
        if isrpc:
            incoming = incoming(forward(outgoing))
        asyncio.create_task(backward(incoming))
        if not isrpc:
            return forward(outgoing)

    def connect(self, address: str, stub: Optional[replica_pb2_grpc.ReplicaStub]=None):
        """Connects to both the Firehose and UserUpdate streams of the peer at the address."""
        if address in self.peers:
            return
        if not stub:
            stub = replica_pb2_grpc.ReplicaStub(grpc.aio.insecure_channel(address))
        self.firehoses = Node(asyncio.Queue(), self.firehoses)
        self.join(
            address,
            self.save,
            stub.Firehose,
            self.firehoses
        )
        self.user_updates = Node(asyncio.Queue(), self.user_updates)
        self.join(
            address,
            self.update_user,
            stub.UserUpdate,
            self.user_updates
        )

    async def Firehose(self, request, context):
        """Accepts an incoming Firehose connection."""
        # Re-sync tables:
        for from_, to, text, sent in self.cursor.execute(
                "SELECT 'from', 'to', text, sent FROM messages ORDER BY sent ASC"
        ):
            time = Timestamp()
            time.FromJsonString(sent)
            yield replica_pb2.ReplicatedMessage(**{
                "message": chat_pb2.Message(
                    username=to,
                    text=text
                ),
                "from": from_,
                "sent": time
            })
        self.firehoses = Node(asyncio.Queue(), self.firehoses)
        async for payload in self.join(
            context.peer(),
            self.save,
            request,
            self.firehoses,
            until=context.cancelled
        ):
            yield payload

    async def UserUpdate(self, request, context):
        """Accepts and incoming UserUpdate connection."""
        # Re-sync tables:
        for name, password in self.cursor.execute(
                "SELECT name, password FROM users"
        ):
            yield chat_pb2.InitialRequest(
                create=True,
                user=chat_pb2.Authentication(
                    username=name,
                    password=password
                )
            )
        self.user_updates = Node(asyncio.Queue(), self.user_updates)
        async for payload in self.join(
            context.peer(),
            self.update_user,
            request,
            self.user_updates,
            until=context.cancelled
        ):
            yield payload

    ### Client-side:

    async def authenticate(self, user, context):
        """Aborts the RPC if authentication fails."""
        if not self.cursor.execute(
            "SELECT EXISTS(SELECT 1 FROM users WHERE name=? AND password=?)",
            user.username,
            user.password
        ).fetchone():
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Incorrect username or password."
            )

    async def Initiate(self, request, context):
        """Accepts a new or existing client."""
        if len(request.user.username.split(maxsplit=1)) != 1:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Username must not contain whitespace or be empty."
            )
        if request.create:
            self.update_user(request)
            self.notify(self.user_updates, request)
            yield chat_pb2.ReceivedMessage() # Heartbeat.
        else:
            await self.authenticate(request.user, context)
            yield chat_pb2.ReceivedMessage() # Heartbeat.
            # Replay persisted messages:
            for username, text, sent in self.cursor.execute(
                    """
                    SELECT 'from', text, sent FROM messages WHERE 'to'=? OR 'from'=?
                    ORDER BY sent ASC
                    """,
                    request.user.username,
                    request.user.username
            ):
                yield chat_pb2.ReceivedMessage(
                    message=chat_pb2.Message(
                        username=username,
                        text=text
                    ),
                    sent=sent
                )
        self.clients[request.user.username] = asyncio.Queue()
        def disconnect(context):
            del self.clients[request.user.username]
        context.add_done_callback(disconnect)
        while not context.cancelled():
            yield await self.clients[request.user.username].get()

    async def SendMessage(self, request, context):
        """Sends message to recipient from the authenticated client."""
        await self.authenticate(request.user, context)
        # Save message, and deliver if recipient is also on this server:
        sent = self.message(
            from_=request.user.username,
            to=request.message.username,
            text=request.message.text
        )
        # Notify peers of new message:
        self.notify(self.firehoses, replica_pb2.ReplicatedMessage(**{
            "from": request.user.username,
            "message": request.message,
            "sent": sent
        }))
        return Empty()

    async def DeleteAccount(self, request, context):
        """Deletes the account of the authenticated client."""
        await self.authenticate(request, context)
        # Delete account on this server:
        update = replica_pb2.InitialRequest(
            create=False,
            user=request
        )
        self.update_user(update)
        # Notify peers:
        self.notify(self.user_updates, update)
        return Empty()

    async def ListUsers(self, request, context):
        """Returns list of all registered users."""
        return chat_pb2.Users(
            usernames=self.cursor.execute(
                "SELECT name FROM users WHERE name GLOB ?",
                request.glob
            )
        )
        
async def serve(chat_port: int,
                replica_port: int,
                servicer: ReplicatedChat,
                timeout: Optional[float]=None):
    async with servicer:
        chat = grpc.aio.server()
        replica = grpc.aio.server()
        replica_pb2_grpc.add_ReplicaServicer_to_server(servicer, replica)
        chat_pb2_grpc.add_ChatServicer_to_server(servicer, chat)
        replica.add_insecure_port(f"[::]:{replica_port}")
        chat.add_insecure_port(f"[::]:{chat_port}")

        await asyncio.gather(
            chat.start(),
            replica.start()
        )
        await asyncio.gather(
            chat.wait_for_termination(timeout),
            replica.wait_for_termination(timeout)
        )

if __name__ == '__main__':
    from os import path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

    import sys
    import argparse
    class Parser(argparse.ArgumentParser):
        def error(self, message):
            print("error: " + message, file=sys.stderr)
            self.print_help()
            sys.exit(2)
    parser = Parser(
        description="Replicated, persistent gRPC server for 262chat."
    )
    parser.add_argument(
        "chat_port",
        type=int,
        help="Which port to serve clients on."
    )
    parser.add_argument(
        "replica_port",
        type=int,
        help="Which port to serve replicas (other servers) on."
    )
    parser.add_argument(
        "database",
        help="Filename of this servers local database.",
        metavar="database.db"
    )
    parser.add_argument(
        "--cluster",
        help="Name of an already-running server in a cluster of replicas to which this server should join.",
        metavar="IP:PORT"
    )
    parser.add_argument(
        "--self-destruct",
        type=float,
        default=None,
        help="For testing purposes: how many minutes to wait before killing self in order to test crash/failstop fault tolerance.",
        metavar="MIN"
    )
    args = parser.parse_intermixed_args()

    from ip import local_ip
    ip = local_ip()
    print(f"Serving clients on {ip}:{args.chat_port} and replicas on {ip}:{args.replica_port}...")
    asyncio.run(serve(
        args.chat_port,
        args.replica_port,
        ReplicatedChat(args.database, args.cluster),
        timeout=args.self_destruct and args.self_destruct*60
    ))
