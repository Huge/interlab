from typing import Any

from ..event import Event
from .base import MemoryBase


class ListMemory(MemoryBase):
    """Simple memory that is effectively just a list of Events"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.events = []

    def add_event(self, event: Event):
        self.events.append(event)

    def get_events(self, query: Any = None, limit: int = None) -> tuple[Event]:
        return tuple(self.events[(-limit if limit is not None else None) :])