from abc import ABC, abstractmethod
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, AsyncIterator

@dataclass
class Message:
    to: str
    text: str
    sent: Optional[datetime]

class AbstractSession(ABC):
    @classmethod
    @abstractmethod
    async def connect(cls, host, port):
        raise NotImplementedError

    @abstractmethod
    async def register(self, username, password):
        raise NotImplementedError

    @abstractmethod
    async def login(self, username, password):
        raise NotImplementedError

    @property
    @abstractmethod
    def username(self):
        raise NotImplementedError

    @abstractmethod
    async def list_users(self, pattern="*"):
        raise NotImplementedError

    @abstractmethod
    async def delete(self):
        raise NotImplementedError

    @abstractmethod
    async def message(self, payload: Message):
        raise NotImplementedError

    @abstractmethod
    async def stream(self) -> AsyncIterator[Message]:
        raise NotImplementedError

    @abstractmethod
    async def close(self):
        raise NotImplementedError

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()
