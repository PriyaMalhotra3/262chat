#/usr/bin/env python3

import sys
import asyncio
import sqlite3
import traceback
from contextlib import asynccontextmanager
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
                 next_: "Optional[Node[T]]"=None,
                 prev: "Optional[Node[T]]"=None):
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

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.remove()
        return False
class LinkedList(Generic[T]):
    def __init__(self):
        self.head: Node[Optional[T]] = Node(None)

    def push(self, value: T) -> Node[T]:
        return Node(value, self.head.next, self.head)

    def __iter__(self) -> Iterable[T]:
        current = self.head.next
        while current:
            yield current.value
            current = current.next

class Replica(replica_pb2_grpc.ReplicaStub):
    def __init__(self, address: str):
        self.address = address
        self.channel = grpc.aio.insecure_channel(self.address)
        super().__init__(self.channel)

    async def __aenter__(self):
        return self

    async def close(self):
        return await self.channel.close()

    async def __aexit__(self, *exc):
        await self.close()
        return False

class ReplicatedChat(chat_pb2_grpc.ChatServicer, replica_pb2_grpc.ReplicaServicer):
    def __init__(self,
                 identity: str,
                 database: str,
                 cluster: Optional[str]=None):
        self.identity = identity
        self.cluster = cluster
        self.database = database
        self.peers: dict[str, Replica] = {}
        self.firehoses = LinkedList()
        self.user_updates = LinkedList()
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

        if self.cluster:
            def outreach(address: str):
                async def consume():
                    async with self.peer(address) as stub:
                        await asyncio.gather(
                            self.subscribe(self.save, stub.Firehose),
                            self.subscribe(self.update_user, stub.UserUpdate)
                        )
                asyncio.create_task(consume())
            # await self.peer(self.cluster).__aenter__()
            initial = self.peers[self.cluster] = Replica(self.cluster)
            for peer in (await initial.Cluster(Empty())).peers:
                outreach(peer)
            outreach(self.cluster)

        return self

    async def __aexit__(self, *exc):
        """Closes connections properly."""
        for peer in self.peers.values():
            await peer.close()
        self.connection.close()
        return False

    ### Peer-side:

    async def subscribe(self,
                        subscriber: Callable,
                        publisher: grpc.aio.UnaryStreamMultiCallable,
                        new: bool=True):
        async for payload in publisher(replica_pb2.Peer(
                new=new,
                address=self.identity
        )):
            try:
                subscriber(payload)
            except sqlite3.IntegrityError:
                # UNIQUE constraint violated, we must have already received the message.
                pass

    @asynccontextmanager
    async def peer(self, address: str):
        """Keeps peer in the known-peers list as long as the connection is unbroken."""
        try:
            peer = self.peers[address]
        except KeyError:
            print("Replica connected: " + address)
            peer = self.peers[address] = Replica(address)
        try:
            async with peer:
                yield peer
        except grpc.aio.AioRpcError as e:
            print(e.details())
        finally:
            try:
                del self.peers[address]
                print("Replica disconnected: " + address)
            except KeyError:
                # Replica already disconnected.
                pass

    async def Cluster(self, request, context):
        """Reports addresses of known peers in this cluster."""
        return replica_pb2.Peers(
            peers=self.peers.keys()
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
        return time

    def save(self, message: replica_pb2.ReplicatedMessage):
        """Saves a ReplicatedMessage to the database."""
        self.message(
            message.from_,
            message.message.username,
            message.message.text,
            message.sent
        )

    def update_user(self, update: chat_pb2.InitialRequest):
        """Performs the update to the users table requested by the InitialRequest."""
        if update.create:
            self.cursor.execute(
                "INSERT INTO users(name, password) VALUES(?, ?)",
                (update.user.username, update.user.password)
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

    async def Firehose(self, request, context):
        """Accepts an incoming Firehose connection."""
        # Re-sync tables:
        for from_, to, text, sent in self.cursor.execute(
                "SELECT [from], [to], text, sent FROM messages ORDER BY sent ASC"
        ):
            time = Timestamp()
            time.FromJsonString(sent)
            yield replica_pb2.ReplicatedMessage(
                message=chat_pb2.Message(
                    username=to,
                    text=text
                ),
                from_=from_,
                sent=time
            )
        if request.new:
            async def consume():
                async with self.peer(request.address) as stub:
                    await self.subscribe(self.save, stub.Firehose, new=False)
            asyncio.create_task(consume())
        async with self.peer(request.address) as stub:
            with self.firehoses.push(asyncio.Queue()) as queue:
                while not context.cancelled():
                    yield await queue.value.get()

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
        if request.new:
            async def consume():
                async with self.peer(request.address) as stub:
                    await self.subscribe(self.update_user, stub.UserUpdate, new=False)
            asyncio.create_task(consume())
        async with self.peer(request.address) as stub:
            with self.user_updates.push(asyncio.Queue()) as queue:
                while not context.cancelled():
                    yield await queue.value.get()

    ### Client-side:

    @staticmethod
    def notify(subscribers: LinkedList[asyncio.Queue], payload):
        """Notifies all subscribers of the new payload."""
        for queue in subscribers:
            queue.put_nowait(payload)

    async def authenticate(self, user, context):
        """Aborts the RPC if authentication fails."""
        if not self.cursor.execute(
            "SELECT EXISTS(SELECT 1 FROM users WHERE name=? AND password=?)",
            (user.username, user.password)
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
                    SELECT [from], text, sent FROM messages WHERE [to]=? OR [from]=?
                    ORDER BY sent ASC
                    """,
                    (request.user.username, request.user.username)
            ):
                time = Timestamp()
                time.FromJsonString(sent)
                yield chat_pb2.ReceivedMessage(
                    message=chat_pb2.Message(
                        username=username,
                        text=text
                    ),
                    sent=time
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
        self.notify(self.firehoses, replica_pb2.ReplicatedMessage(
            from_=request.user.username,
            message=request.message,
            sent=sent
        ))
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
            usernames=(row[0] for row in self.cursor.execute(
                "SELECT name FROM users WHERE name GLOB ?",
                (request.glob,)
            ))
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
    identity = f"{ip}:{args.replica_port}"
    print(f"Serving clients on {ip}:{args.chat_port} and replicas on {identity}...")
    asyncio.run(serve(
        args.chat_port,
        args.replica_port,
        ReplicatedChat(identity, args.database, args.cluster),
        timeout=args.self_destruct and args.self_destruct*60
    ))
