import sys
import unittest
import asyncio
import asyncio.subprocess
import socket

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
            sys.executable, "-m", self.server,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.DEVNULL,
            env={
                "PORT": str(self.port)
            }
        )
        await asyncio.sleep(1)
        self.addAsyncCleanup(self.server_process.terminate)
        self.session = await self.client.connect("localhost", self.port)
        self.addAsyncCleanup(self.session.close)

    async def test_register(self):
        await self.session.register("Alice", "pass")

    async def test_login(self):
        await self.session.register("Alice", "pass")
        await self.session.close()
        self.session = await self.client.connect("localhost", self.port)
        await self.session.login("Alice", "pass")

class TestPart1(TestAbstractSession, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = "part1.server"
        self.client = Part1Session
        await super().asyncSetUp()

class TestPart2(TestAbstractSession, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = "part2.server"
        self.client = Part2Session
        await super().asyncSetUp()

if __name__ == "__main__":
    unittest.main()
