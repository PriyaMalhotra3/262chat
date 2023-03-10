#/usr/bin/env python3

import os
import socketserver
import fnmatch
from datetime import datetime, timezone
from threading import Lock, RLock
from queue import Queue, SimpleQueue, Empty
from dataclasses import dataclass, field
from typing import Optional

CHUNK_SIZE = 4096

@dataclass
class User:
    username: str
    password: str
    session: Optional["Session"] = field(default=None, compare=False)
    queue: Queue[str] = field(default_factory=SimpleQueue, compare=False)
    lock: Lock = field(default_factory=Lock, compare=False)

    def send(self, message):
        try:
            self.session.send(message)
        except:
            self.queue.put(message)
users : dict[str, User] = {}
users_lock = Lock()

class ProtocolException(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return "ERROR " + self.message

class SessionDeath(Exception):
    pass

class Session(socketserver.BaseRequestHandler):
    def setup(self):
        self.socket = self.request
        self.transfer_buffer = bytearray()
        self.lock = RLock()
        self.user = None

    def _log(self, text, receiving=False):
        ip, port = self.socket.getpeername()
        label = f"{ip}:{port}"
        if receiving:
            label += " -> "
        else:
            label += " <- "
        first = True
        for line in text.splitlines():
            print(
                (
                    label
                    if first
                    else " "*len(label)
                )
                + line
            )
            first = False

    def _readstring(self):
        "Not thread-safe."
        terminator = self.transfer_buffer.find(0)
        while terminator < 0:
            try:
                chunk = self.socket.recv(CHUNK_SIZE)
            except Exception:
                raise SessionDeath
            if not chunk:
                raise SessionDeath
            self.transfer_buffer.extend(chunk)
            terminator = self.transfer_buffer.find(0)
        result = self.transfer_buffer[:terminator].decode("utf-8")
        del self.transfer_buffer[:terminator + 1]
        self._log(result, True)
        return result

    def send(self, message):
        "Thread-safe."
        text = str(message)
        self._log(text)
        encoded = text.encode("utf-8")
        if b"\0" in encoded:
            raise ValueError("Message cannot contain premature null bytes.")
        with self.lock:
            try:
                self.socket.sendall(encoded + b"\0")
            except Exception:
                raise SessionDeath

    def associate(self) -> User:
        try:
            command, username = self._readstring().split()
        except ValueError as e:
            raise ProtocolException("Username must not contain whitespace or be empty.")

        password = self._readstring()

        if command == "REGISTER":
            with users_lock:
                if username in users:
                    raise ProtocolException(f'Username "{username}" is not available.')
                users[username] = self.user = User(username, password, self)
                self.user.lock.acquire()
        elif command == "LOGIN":
            try:
                user = users[username]
            except KeyError:
                raise ProtocolException("Incorrect username.")
            if user.password != password:
                raise ProtocolException("Incorrect password.")
            if not user.lock.acquire(blocking=False):
                ip, port = self.socket.getpeername()
                user.send(f"ADMIN Someone from {ip}:{port} tried to log in as you and guessed your password correctly.")
                raise ProtocolException(f"{username} is already logged in; are you trying to break in?")
            self.user = user
        else:
            raise ProtocolException("Must LOGIN or REGISTER to begin session.")

    def list_users(self, pattern="*"):
        self.send("LISTING\n"
                  + "\n".join(username
                              + (" (online)"
                                 if users[username].session
                                 else "")
                              for username in fnmatch.filter(users, pattern)))

    def delete(self):
        with users_lock:
            del users[self.user.username]
            self.send("DELETED Account deleted; you are being disconnected.")
            raise SessionDeath

    def message(self, to, text):
        try:
            recipient = users[to]
        except KeyError:
            raise ProtocolException(f"{to} is not a user; try LIST to see available users.")
        recipient.send("MESSAGE " + self.user.username + "\n"
                       + "Sent: " + datetime.now(timezone.utc).isoformat() + "\n"
                       + text)
        self.send("SENT")

    def handle(self):
        try:
            while not self.user:
                try:
                    self.associate()
                    self.send("SUCCESS You are logged in.")
                except ProtocolException as e:
                    self.send(e)
            with self.lock:
                self.user.session = self
                try:
                    while True:
                        self.send(self.user.queue.get(block=False))
                except Empty:
                    pass
            while True:
                command = self._readstring().split(maxsplit=1)
                if command[0] == "DELETE":
                    self.delete()
                elif command[0] == "LIST":
                    self.list_users(*command[1:])
                elif command[0] == "MESSAGE":
                    try:
                        to, message = command[1].split(maxsplit=1)
                        self.message(to, message)
                    except (ValueError, KeyError) as e:
                        self.send(ProtocolException("Incorrect message format."))
                    except ProtocolException as e:
                        self.send(e)
                else:
                    self.send(ProtocolException("Unknown command."))
        except SessionDeath:
            pass

    def finish(self):
        if self.user:
            self.user.session = None
            self.user.lock.release()

def serve(address: tuple[str, int]):
    with socketserver.ThreadingTCPServer(address, Session) as server:
        server.serve_forever()

if __name__ == "__main__":
    # We are running as a script right now, so go ahead and start the server:
    import sys
    from os import path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
    from ip import local_ip
    ip = local_ip()
    port = int(os.getenv("PORT", 8080))
    print(f"Serving on {ip}:{port}...")
    serve(("0.0.0.0", port))
