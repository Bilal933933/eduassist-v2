"""عقود الأحداث (Event Contracts) — تعريف موحد لأحداث البث."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """أنواع الأحداث في نظام البث."""

    TOKEN = "token"
    STATUS = "status"
    CITATION = "citation"
    CLARIFICATION = "clarification"
    TRACE = "trace"
    DONE = "done"
    ERROR = "error"


@dataclass
class StreamEvent:
    """حدث بث موحد. لا يعرف شيئًا عن SSE أو WebSocket."""

    type: EventType
    thread_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    seq: int = 0
    version: int = 1
