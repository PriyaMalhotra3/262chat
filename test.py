import os
os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "false"

import sys
import unittest
import asyncio
import asyncio.subprocess
import socket
from pathlib import Path
from typing import AsyncIterator

from interface import Message
from part1.client import Session as Part1Session
from part2.client import Session as Part2Session

class TestAbstractSession:
    @staticmethod
    def free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("", 0))
            return sock.getsockname()[1]

    async def asyncSetUp(self):
        self.port = self.free_port()
        self.server_process = await asyncio.create_subprocess_exec(
            sys.executable, (Path(__file__).parent / self.server).resolve(),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            env=dict(os.environ, PORT=str(self.port))
        )
        await asyncio.sleep(1) # Wait for service to come up and open port.

    def tearDown(self):
        self.server_process.terminate

    async def connect(self):
        session = await self.client.connect("localhost", self.port)
        self.addAsyncCleanup(session.close)
        return session 

    async def test_register(self):
        alice = await self.connect()
        await alice.register("Alice", "pass")

    async def test_register_empty(self):
        client = await self.connect()
        with self.assertRaisesRegex(Exception, r"empty"):
            await client.register("", "pass")

    async def test_register_invalid_name(self):
        with self.assertRaisesRegex(Exception, r"must not contain whitespace"):
            client = await self.connect()
            await client.register("white space", "pass")

    async def test_register_collision(self):
        alice1 = await self.connect()
        await alice1.register("Alice", "pass")

        alice2 = await self.connect()
        with self.assertRaisesRegex(Exception, r"not available"):
            await alice2.register("Alice", "pass")

    async def test_login(self):
        alice = await self.connect()
        await alice.register("Alice", "pass")
        await alice.close()

        alice_later = await self.connect()
        await alice_later.login("Alice", "pass")

    async def test_login_incorrect_password(self):
        alice = await self.connect()
        await alice.register("Alice", "pass")
        await alice.close()

        someone_else = await self.connect()
        with self.assertRaisesRegex(Exception, r"Incorrect password"):
            await someone_else.login("Alice", "incorrect")

    async def test_login_nonexistent(self):
        alice = await self.connect()
        with self.assertRaisesRegex(Exception, r"Incorrect username"):
            await alice.login("Alice", "pass")

    async def test_username(self):
        alice = await self.connect()
        await alice.register("Alice", "pass")
        self.assertEqual(alice.username, "Alice")

    def assert_users_equal(self, *username_lists: list[str]):
        username_sets = [
            set(
                username.split()[0]
                for username in usernames
            )
            for usernames in username_lists
        ]
        for current, upcoming in zip(username_sets, username_sets[1:]):
            self.assertSetEqual(current, upcoming)

    async def test_list_users(self):
        alice = await self.connect()
        await alice.register("Alice", "pass")

        bob = await self.connect()
        await bob.register("Bob", "otherpass")

        self.assert_users_equal(
            await alice.list_users(),
            await bob.list_users(),
            ["Alice", "Bob"]
        )

    async def test_list_pattern(self):
        alice = await self.connect()
        await alice.register("Alice", "pass")

        alvin = await self.connect()
        await alvin.register("Alvin", "pass")

        bob = await self.connect()
        await bob.register("Bob", "pass")

        self.assert_users_equal(
            await alice.list_users("Al*"),
            await bob.list_users(  "Al*"),
            await alvin.list_users("Al*"),
            ["Alice", "Alvin"]
        )

    async def assert_messages_equal(self, stream: AsyncIterator[Message], messages: list[Message]):
        if not messages:
            return
        i = 0
        async for message in stream:
            expected = messages[i]
            self.assertEqual(expected.to,   message.to)
            self.assertEqual(expected.text, message.text)
            i += 1
            if i >= len(messages):
                return

    async def test_messaging(self):
        alice = await self.connect()
        await alice.register("Alice", "pass")

        bob = await self.connect()
        await bob.register("Bob", "pass")

        await alice.message(Message("Bob", "Hi Bob"))
        await self.assert_messages_equal(bob.stream(), [Message("Alice", "Hi Bob")])

        await bob.message(Message("Alice", "Hi Alice"))
        await self.assert_messages_equal(alice.stream(), [Message("Bob", "Hi Alice")])

        multiple = [
            "Crazy weather we've been having",
            "We should grab a meal sometime",
            "How've you been?"
        ]
        for text in multiple:
            await alice.message(Message("Bob", text))
        await self.assert_messages_equal(
            bob.stream(),
            [
                Message("Alice", text)
                for text in multiple
            ]
        )

    async def test_queueing(self):
        alice = await self.connect()
        await alice.register("Alice", "pass")

        bob = await self.connect()
        await bob.register("Bob", "pass")

        await alice.message(Message("Bob", "Hi Bob"))
        await self.assert_messages_equal(bob.stream(), [Message("Alice", "Hi Bob")])

        await alice.close()
        messages = [
            "Say, about that meal you were talking about...",
            "Hey, where'd you go?",
            "Okay, bye"
        ]
        for text in messages:
            await bob.message(Message("Alice", text))
        await bob.close()

        alice_later = await self.connect()
        await alice_later.login("Alice", "pass")
        await self.assert_messages_equal(
            alice_later.stream(),
            [
                Message("Bob", text)
                for text in messages
            ]
        )

    async def test_delete(self):
        alice = await self.connect()
        await alice.register("Alice", "pass")

        bob = await self.connect()
        await bob.register("Bob", "otherpass")

        self.assert_users_equal(
            await alice.list_users(),
            await bob.list_users(),
            ["Alice", "Bob"]
        )

        await alice.delete()
        self.assert_users_equal(
            await bob.list_users(),
            ["Bob"]
        )

class TestPart1(TestAbstractSession, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = "./part1/server.py"
        self.client = Part1Session
        await super().asyncSetUp()

class TestPart2(TestAbstractSession, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = "./part2/server.py"
        self.client = Part2Session
        await super().asyncSetUp()

if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    except RuntimeError as e:
        if e.args[0] != "Event loop is closed":
            raise
