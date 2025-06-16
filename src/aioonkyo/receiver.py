"""Receiver."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import Final, Generic, Self, TypeVar

from .common import BasicReceiverInfo, ReceiverInfo
from .instruction import Instruction
from .protocol import (
    DiscoveryInfo,
    EISCPDiscovery,
    OnkyoConnectionError,
    read_messages,
    write_messages,
)
from .status import Status

_LOGGER = logging.getLogger(__name__)


BROADCAST_ADDRESS: Final = "255.255.255.255"


async def async_interview(
    host: str,
    *,
    port: int = 60128,
) -> ReceiverInfo:
    """Interview Onkyo Receiver."""

    target_str = f"{host}:{port}"
    _LOGGER.debug("Interviewing receiver: %s", target_str)

    receiver_info_future: asyncio.Future[ReceiverInfo] = asyncio.Future()

    def callback(discovery: DiscoveryInfo) -> None:
        """Receiver interviewed, connection not yet active."""
        if receiver_info_future.done():
            return
        receiver_info = ReceiverInfo(
            host=host,
            ip=discovery.ip,
            port=discovery.iscp_port,
            model_name=discovery.model_name,
            identifier=discovery.identifier,
        )
        receiver_info_future.set_result(receiver_info)

    protocol = EISCPDiscovery(target_str, callback)

    loop = asyncio.get_running_loop()
    await loop.create_datagram_endpoint(lambda: protocol, remote_addr=(host, port))

    try:
        receiver_info = await receiver_info_future
    finally:
        protocol.close()

    _LOGGER.debug("Interviewed receiver %s: %s", target_str, receiver_info)

    return receiver_info


async def async_discover(
    address: str = BROADCAST_ADDRESS,
    *,
    port: int = 60128,
) -> AsyncGenerator[ReceiverInfo]:
    """Discover Onkyo Receivers."""

    target_str = f"{address}:{port}"
    _LOGGER.debug("Discovering receivers on %s", target_str)

    receivers_discovered: set[str] = set()
    receiver_info_queue: asyncio.Queue[ReceiverInfo] = asyncio.Queue()

    def callback(discovery: DiscoveryInfo) -> None:
        """Receiver discovered, connection not yet active."""
        info = ReceiverInfo(
            host=discovery.ip,
            ip=discovery.ip,
            port=discovery.iscp_port,
            model_name=discovery.model_name,
            identifier=discovery.identifier,
        )
        if info.identifier not in receivers_discovered:
            receivers_discovered.add(info.identifier)
            receiver_info_queue.put_nowait(info)

    protocol = EISCPDiscovery(target_str, callback)

    loop = asyncio.get_running_loop()
    await loop.create_datagram_endpoint(
        lambda: protocol,
        remote_addr=(address, port),
        allow_broadcast=True,
    )

    try:
        while True:
            receiver_info = await receiver_info_queue.get()
            _LOGGER.debug("Discovered receiver on %s: %s", target_str, receiver_info)
            yield receiver_info
    finally:
        protocol.close()


InfoT = TypeVar("InfoT", bound=BasicReceiverInfo, default=ReceiverInfo)


@contextmanager
def _yield_receiver(receiver: Receiver[InfoT]) -> Generator[Receiver[InfoT]]:
    """Connect to the receiver."""
    try:
        yield receiver
    finally:
        receiver.close()


@asynccontextmanager
async def _async_connect(info: InfoT) -> AsyncGenerator[Receiver[InfoT]]:
    """Connect to the receiver."""
    receiver = await Receiver.open_connection(info)
    with _yield_receiver(receiver) as receiver:
        yield receiver


@asynccontextmanager
async def _async_connect_retry(info: InfoT) -> AsyncGenerator[Receiver[InfoT]]:
    """Connect to the receiver, retrying on failure."""
    sleep_time = 10
    sleep_time_max = 180
    while True:
        try:
            receiver = await Receiver.open_connection(info)
        except OSError:
            await asyncio.sleep(sleep_time)
            sleep_time = min(sleep_time * 2, sleep_time_max)
        else:
            break
    with _yield_receiver(receiver) as receiver:
        yield receiver


@asynccontextmanager
async def async_connect(info: InfoT, *, retry: bool = False) -> AsyncGenerator[Receiver[InfoT]]:
    """Connect to the receiver."""
    _LOGGER.debug("Async context manager connect (retry: %s): %s", retry, info)
    connect = _async_connect_retry if retry else _async_connect
    async with connect(info) as receiver:
        yield receiver


class _ReceiverState(Enum):
    """Receiver state."""

    IDLE = "idle"
    RUNNING = "running"
    CLOSED = "closed"


@dataclass
class Receiver(Generic[InfoT]):
    """Receiver (connected)."""

    info: InfoT
    _reader: asyncio.StreamReader
    _writer: asyncio.StreamWriter
    _read_queue: asyncio.Queue[Status] = field(default_factory=asyncio.Queue)
    _write_queue: asyncio.Queue[Instruction] = field(default_factory=asyncio.Queue)
    _state: _ReceiverState = _ReceiverState.IDLE

    @classmethod
    async def open_connection(cls, info: InfoT) -> Self:
        """Open connection to the receiver."""
        _LOGGER.debug("Connecting: %s", info)
        reader, writer = await asyncio.open_connection(info.host, info.port)
        _LOGGER.debug("Connected: %s", info)
        return cls(info, reader, writer)

    async def run(self) -> None:
        """Run reader/writer."""
        if self._state is not _ReceiverState.IDLE:
            raise RuntimeError(
                "Run called on receiver not in IDLE state, "
                f"current state: {self._state}, info: {self.info}"
            )
        try:
            _LOGGER.debug("Run starting: %s", self.info)
            self._state = _ReceiverState.RUNNING
            async with asyncio.TaskGroup() as tg:
                tg.create_task(read_messages(self._reader, self._read_queue, self.info))
                tg.create_task(write_messages(self._writer, self._write_queue, self.info))
        except* OnkyoConnectionError as exc:
            _LOGGER.warning("Disconnect detected (%s): %s", exc.exceptions, self.info)
        finally:
            _LOGGER.debug("Run ending: %s", self.info)
            self._close()

    async def read(self) -> Status | None:
        """Read from the receiver."""
        if self._state is _ReceiverState.CLOSED:
            return None
        try:
            message = await self._read_queue.get()
            _LOGGER.debug("[%s] <<<< %s", self.info.host, message)
        except asyncio.QueueShutDown:
            return None
        else:
            return message

    async def write(self, message: Instruction) -> None:
        """Write to the receiver."""
        if self._state is _ReceiverState.CLOSED:
            raise RuntimeError(f"Write called on receiver in CLOSED state, info: {self.info}")
        _LOGGER.debug("[%s] >>   %s", self.info.host, message)
        self._write_queue.put_nowait(message)

    def _close(self) -> None:
        """Close connection."""
        if self._state is _ReceiverState.CLOSED:
            _LOGGER.debug("Closing - already closed: %s", self.info)
            return

        _LOGGER.debug("Closing - cleaning up: %s", self.info)
        self._state = _ReceiverState.CLOSED
        self._writer.close()  # writer closes the whole stream, including the reader
        self._read_queue.shutdown(immediate=True)

    def close(self) -> None:
        """Close connection."""
        if self._state is _ReceiverState.RUNNING:
            raise RuntimeError(f"Close called on receiver in RUNNING state, info: {self.info}")
        self._close()


class BasicReceiver(Receiver[BasicReceiverInfo]):
    """Basic receiver (connected)."""


__all__ = [
    "async_interview",
    "async_discover",
    "async_connect",
    "Receiver",
]
