import os
import socketserver
from datetime import datetime, timezone
from threading import Lock, RLock
from queue import Queue, SimpleQueue, Empty

CHUNK_SIZE = 4096

class User:
    def __init__(username: str, password: str, session):
        self.username = username
        self.password = password
        self.session = session
        self.queue = SimpleQueue()
        self.lock = Lock()
        # Automatically acquire the lock on this user upon initialization.
        lock.acquire()

    def send(self, message):
        try:
            self.session.send(message)
        except TypeError:
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
        self.transfer_buffer = b""
        self.lock = RLock()
        self.user = None

    def readstring(self):
        "Not thread-safe."
        parted = (self.transfer_buffer, b"", b"")
        while len(parted[1]) == 0:
            chunk = socket.recv(4096)
            if not chunk:
                raise SessionDeath
            transfer_buffer += chunk
            parted = transfer_buffer.partition(b"\0")
        transfer_buffer = parted[2]
        return parted[0].decode("utf-8")

    def send(self, message):
        "Thread-safe."
        if "\0" in message:
            raise ValueError("Message cannot contain premature null bytes.")
        with lock:
            self.socket.sendall(str(message).encode("utf-8") + b"\0")

    def associate(self) -> User:
        try:
            command, username = readstring().split()
        except ValueError as e:
            raise ProtocolException("Must LOGIN or REGISTER with username to begin session: " + e.args[0])

        password = readstring()

        if command == "REGISTER":
            with users_lock:
                if username in users:
                    raise ProtocolException(f'Username "{username}" is not available.')
                users[username] = self.user = User(username, password, self)
        elif command == "LOGIN":
            try:
                user = users[username]
            except KeyError:
                raise ProtocolException("Incorrect username or password.")
            if user.password != password:
                raise ProtocolException("Incorrect username or password.")
            if not user.lock.acquire(blocking=False):
                user.send(f"ADMIN Someone from {client_address[0]}:{client_address[1]} tried to log in as you and guessed your password correctly.")
                raise ProtocolException(f"{username} is already logged in; are you trying to break in?")
            self.user = user
        else:
            raise ProtocolException("Must LOGIN or REGISTER to begin session.")

    def list_users(self):
        self.send("ADMIN\n"
                  + "\n".join(username
                              + (" (online)"
                                 if user.session is not None
                                 else "")
                              for username, user in users))

    def delete(self):
        with users_lock:
            del users[self.user.username]
            self.send("SUCCESS Account deleted; you are being disconnected.")
            raise SessionDeath

    def message(self, to, message):
        try:
            recipient = users[to]
        except KeyError:
            raise ProtocolException(f"{to} is not a user; try LIST to see available users.")
        recipient.send("MESSAGE " + self.user.username + "\n"
                       + "Sent: " + datetime.now(timezone.utc).isoformat() + "\n"
                       + message)
        self.send("SENT")

    def handle(self):
        while self.user is None:
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
        try:
            while True:
                command = readstring()
                if command == "LIST":
                    self.list_users()
                elif command == "DELETE":
                    self.delete()
                elif command.startswith("MESSAGE"):
                    try:
                        _, to, message = command.split(maxsplit=2)
                    except ValueError as e:
                        self.send(ProtocolException("Incorrect message format: " + e.args[0]))
                    except ProtocolException as e:
                        self.send(e)
                else:
                    self.send(ProtocolException("Unknown command."))
        except SessionDeath:
            pass

    def finish(self):
        self.user.session = None
        self.user.lock.release()

def serve(address: tuple[str, int]):
    with socketserver.ThreadingTCPServer(address, Session) as server:
        print(f"Serving on {address[0]}:{address[1]}...")
        server.serve_forever()

if __name__ == "__main__":
    # We are running as a script right now, so go ahead and start the server:
    serve(("localhost", int(os.getenv("PORT", 8080))))
