"""WebSocket endpoints."""

import asyncio
import os
import sys
import threading
import time
from collections import deque
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Sequence

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic_core import to_json
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

__all__ = ["router", "capture_output", "broadcast"]


class MsgType(StrEnum):
    """Types of messages sent over WebSocket."""

    LOG = "log"
    ERROR = "error"
    UPDATE = "update"


class ConnectionManager:
    """Manages WebSocket connections and broadcasts messages to all connected
    clients."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        log_path: Path,
        log_limit: int = 1000,
    ) -> None:
        self.loop = loop
        self.log_path = log_path
        self.log_buffer: deque[str] = deque(maxlen=log_limit)
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        """Accept a new WebSocket connection and send old logs to the new client."""
        await ws.accept()
        self.active.append(ws)
        # send old logs to the new client
        if self.log_path.exists():
            for line in self.log_path.read_text("utf-8").splitlines():
                data = {"type": "log", "data": {"text": line, "override": False}}
                text = to_json(data).decode("utf-8")
                await ws.send_text(text)

    def disconnect(self, ws: WebSocket):
        """Remove a WebSocket connection from the active list."""
        self.active.remove(ws)

    def broadcast(self, msg_type: MsgType, data: Any) -> None:
        """Broadcast a message to all connected WebSocket clients and append it
        to the log file."""
        if self.loop and manager:
            asyncio.run_coroutine_threadsafe(self._broadcast(msg_type, data), self.loop)

    async def _broadcast(self, msg_type: MsgType, data: Any) -> None:
        if msg_type == MsgType.LOG:
            assert isinstance(data, str)
            override = (
                data.startswith("\r")
                and len(self.log_buffer) > 0
                and self.log_buffer[-1].endswith("\n")
            )
            if override:
                # handle progress bar updates (e.g. tqdm, yt-dlp) that overwrite
                # the same line
                data = data[1:]
                if not data.endswith("\n"):
                    data += "\n"
                self.log_buffer.pop()
            self.log_buffer.append(data)
            self.log_path.write_text("".join(self.log_buffer), encoding="utf-8")
            data = {"text": data, "override": override}

        for ws in list(self.active):
            try:
                text = to_json({"type": msg_type, "data": data}).decode("utf-8")
                await ws.send_text(text)
            except Exception:  # pylint: disable=broad-except
                self.disconnect(ws)


manager: ConnectionManager | None = None  # pylint: disable=invalid-name


def broadcast(msg_type: MsgType, data: Any) -> None:
    """Broadcast a message to all connected WebSocket clients."""
    if manager:
        manager.broadcast(msg_type, data)


class FdCapture:
    """Redirects a file descriptor (e.g. stdout, stderr) to a pipe.
    A background thread tees output to the original fd and broadcasts it."""

    def __init__(self, fd: int, tee: bool = True) -> None:
        """
        Args:
            fd: File descriptor to capture.
            tee: If True, also write output to the original fd (e.g. terminal).
        """
        self.fd = fd
        self.tee = tee

        self.original_fd = os.dup(fd)
        self.r, self.w = os.pipe()
        os.dup2(self.w, fd)  # redirect fd -> pipe write end
        os.close(self.w)

        # Also redirect Python's high-level stream
        if fd == 1:
            sys.stdout = os.fdopen(os.dup(fd), "w", buffering=1)
        elif fd == 2:
            sys.stderr = os.fdopen(os.dup(fd), "w", buffering=1)

        self.thread = threading.Thread(target=self.drain_and_broadcast, daemon=True)
        self.thread.start()

    def drain_and_broadcast(self):
        """Read from the pipe and broadcast to WebSocket clients."""
        with os.fdopen(self.r, "rb") as pipe:
            for raw in iter(lambda: pipe.read1(4096), b""):  # type: ignore[attr-defined]
                text = raw.decode(errors="replace")
                if self.tee:
                    os.write(self.original_fd, raw)  # tee to terminal
                broadcast(MsgType.LOG, text)

    def restore(self):
        """Restore the original file descriptor."""
        os.dup2(self.original_fd, self.fd)
        os.close(self.original_fd)
        if self.fd == 1:
            sys.stdout = sys.__stdout__
        elif self.fd == 2:
            sys.stderr = sys.__stderr__
        self.thread.join(timeout=1)


@contextmanager
def capture_output(loop: asyncio.AbstractEventLoop, log_path: Path, tee: bool = True):
    """Context manager to capture stdout and stderr and broadcast them to
    WebSocket clients."""
    global manager  # pylint: disable=global-statement
    manager = ConnectionManager(loop, log_path)
    captures = [FdCapture(1, tee), FdCapture(2, tee)]  # stdout, stderr
    try:
        yield
    finally:
        for c in reversed(captures):
            c.restore()


class DebouncedWebSocketHandler(FileSystemEventHandler):
    """A watchdog event handler that sends debounced websocket messages."""

    def __init__(
        self,
        what: str,
        payload_fn: Callable[[], Any],
        event_types: Sequence[str] | None = None,
        debounce_seconds: float | None = None,
    ):
        super().__init__()
        self.what = what
        self.payload_fn = payload_fn
        self.event_types = event_types
        self.debounce_seconds = debounce_seconds
        self.last_event_time = 0.0

    def on_any_event(self, event: FileSystemEvent) -> None:
        # skip directories and non-matching event types
        if event.is_directory or (
            self.event_types is not None and event.event_type not in self.event_types
        ):
            return

        # fire only every debounce_seconds to avoid fetch this payload too often or
        # flooding the websocket with too many messages
        now = time.perf_counter()
        if (
            self.debounce_seconds is not None
            and now - self.last_event_time < self.debounce_seconds
        ):
            return
        self.last_event_time = now

        # send the update message to all connected websocket clients
        data = {
            "what": self.what,
            "payload": self.payload_fn(),
            "trigger": event.src_path,
            "reason": event.event_type,
        }
        broadcast(MsgType.UPDATE, data)


def fs_watch(
    what: str,
    path: Path | str,
    payload_fn: Callable[[], Any],
    event_types: Sequence[str] | None = ("created", "modified", "deleted", "moved"),
    debounce_seconds: float = 0.1,
):
    """Watch a file or directory for changes.

    Args:
        what: A string describing what is being watched. Can be used by the client to
            differentiate between different types of updates/payloads.
        path: The path to the file or directory to watch.
        payload_fn: A function that returns the payload to send to the websocket
            when a change is detected.
        event_types: A list of event types to watch for.
        debounce_seconds: Minimum time in seconds between consecutive websocket
            messages. This is useful to avoid flooding the websocket with too many
            messages when a file is being written to in multiple steps.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Cannot watch '{what}': {path} does not exist.")

    handler = DebouncedWebSocketHandler(
        what=what,
        payload_fn=payload_fn,
        event_types=event_types,
        debounce_seconds=debounce_seconds,
    )
    observer = Observer()
    observer.schedule(handler, str(path), recursive=path.is_dir())
    observer.start()
    return observer


router = APIRouter()


@router.delete("/api/clear-log")
async def api_clear_log():
    """Clear the server log."""
    if manager:
        manager.log_buffer.clear()
        manager.log_path.write_text("", encoding="utf-8")


@router.websocket("/ws")
async def ws_logs(ws: WebSocket):
    """WebSocket endpoint for streaming logs and errors to the client
    (uni-directional)."""
    if not manager:
        await ws.close()
        return
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(ws)
