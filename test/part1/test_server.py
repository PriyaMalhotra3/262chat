import socket
import unittest
from unittest.mock import patch, Mock
from io import StringIO

from part1 import server

@patch("sys.stdout", Mock())
@patch("socket.socket.getpeername", Mock(return_value=("tester", 0)))
@patch.dict("part1.server.users", {}, clear=True)
class TestSession(unittest.TestCase):
    @patch("socket.socket")
    def test_register(self, sock):
        # Start a new session with the mocked socket:
        session = server.Session.__new__(server.Session)
        session.request = sock
        session.setup()

        # Queue up the messages:
        sock.recv.side_effect = [
            b"REGISTER Alice\0pass\0",
            # Mock a dropped connection after everything is sent:
            None
        ]

        # Run loop until all messages processed:
        session.handle()

        # Assert expected post-conditions:
        sock.recv.assert_called()
        sock.sendall.assert_called_once_with(b"SUCCESS You are logged in.\0")
        assert len(server.users) == 1
        assert server.users["Alice"] == server.User("Alice", "pass", session)
        assert session.user == server.users["Alice"]

    @patch("socket.socket")
    @patch.dict("part1.server.users", {
        "Alice": server.User("Alice", "pass")
    })
    def test_register_collision(self, sock):
        # Start a new session with the mocked socket:
        session = server.Session.__new__(server.Session)
        session.request = sock
        session.setup()

        # Queue up the messages:
        sock.recv.side_effect = [
            b"REGISTER Alice\0pass\0",
            # Mock a dropped connection after everything is sent:
            None
        ]

        # Run loop until all messages processed:
        session.handle()

        # Assert expected post-conditions:
        sock.recv.assert_called()
        sock.sendall.assert_called_once_with(b'ERROR Username "Alice" is not available.\0')
        assert not session.user

    @patch("socket.socket")
    @patch.dict("part1.server.users", {
        "Alice": server.User("Alice", "pass")
    })
    def test_login(self, sock):
        # Start a new session with the mocked socket:
        session = server.Session.__new__(server.Session)
        session.request = sock
        session.setup()

        # Queue up the messages:
        sock.recv.side_effect = [
            b"LOGIN Alice\0pass\0",
            None
        ]

        # Run loop until all messages processed:
        session.handle()

        # Assert expected post-conditions:        
        sock.recv.assert_called()
        sock.sendall.assert_called_once_with(b"SUCCESS You are logged in.\0")
        assert session.user == server.users["Alice"] # Should have found right user.

    @patch("socket.socket")
    @patch.dict("part1.server.users", {
        "Alice": server.User("Alice", "pass")
    })
    def test_login_wrong_password(self, sock):
        # Start a new session with the mocked socket:
        session = server.Session.__new__(server.Session)
        session.request = sock
        session.setup()

        # Queue up the messages:
        sock.recv.side_effect = [
            b"LOGIN Alice\0incorrect\0",
            None
        ]

        # Run loop until all messages processed:
        session.handle()

        # Assert expected post-conditions:        
        sock.recv.assert_called()
        sock.sendall.assert_called_once_with(b"ERROR Incorrect password.\0")
        assert not session.user

    @patch("socket.socket")
    def test_login_nonexistent(self, sock):
        # Start a new session with the mocked socket:
        session = server.Session.__new__(server.Session)
        session.request = sock
        session.setup()

        # Queue up the messages:
        sock.recv.side_effect = [
            b"LOGIN Alice\0pass\0",
            None
        ]

        # Run loop until all messages processed:
        session.handle()

        # Assert expected post-conditions:        
        sock.recv.assert_called()
        sock.sendall.assert_called_once_with(b"ERROR Incorrect username.\0")
        assert not session.user
