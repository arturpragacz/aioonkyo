"""Protocol."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import cached_property
import logging
import struct
from typing import ClassVar, Self

from .common import BasicReceiverInfo, OnkyoError
from .instruction import DiscoveryQuery, Instruction
from .message import Message
from .message_code import Code
from .parameter import DestinationArea
from .status import DiscoveryStatus, NotAvailableStatus, RawStatus, Status, status_classes

_LOGGER = logging.getLogger(__name__)


class OnkyoConnectionError(OnkyoError):
    """Onkyo connection error."""


class OnkyoParsingError(OnkyoError):
    """Onkyo parsing error."""


class OnkyoStreamRecoverableError(OnkyoError):
    """Onkyo stream recoverable error."""


class ParseMode(Enum):
    """Parse mode."""

    ISCP = auto()
    EISCP = auto()
    DISCOVERY = auto()


@dataclass
class EISCPPacket[M: Message]:
    """eISCP packet."""

    header: EISCPHeader
    iscp: ISCPData[M]

    @staticmethod
    def parse_status(
        packet_plus: bytes, *, parse_mode: ParseMode = ParseMode.EISCP
    ) -> EISCPPacket[Status]:
        """Parse the eISCP status packet from reader."""
        header = EISCPHeader.parse(packet_plus)
        if len(packet_plus) < header.total_size:
            raise OnkyoParsingError(
                f"Too short eISCP packet: {len(packet_plus)} < {header.total_size}.\n"
                f"Packet plus: {packet_plus!r}"
            )
        data = packet_plus[header.header_size : header.total_size]
        iscp = ISCPStatusData.parse(data, parse_mode=parse_mode)
        return EISCPPacket(header, iscp)

    @staticmethod
    async def parse_status_read(
        reader: asyncio.StreamReader, *, parse_mode: ParseMode = ParseMode.EISCP
    ) -> EISCPPacket[Status]:
        """Parse the eISCP status packet from reader."""
        header = await EISCPHeader.parse_read(reader)
        data = await reader.readexactly(header.data_size)
        iscp = ISCPStatusData.parse(data, parse_mode=parse_mode)
        return EISCPPacket(header, iscp)

    @staticmethod
    def from_instruction_message(
        message: Instruction, unit_type: UnitType | None = None
    ) -> EISCPPacket[Instruction]:
        """Create eISCP packet from instruction message."""
        if unit_type is None:
            data = ISCPInstructionData(message)
        else:
            data = ISCPInstructionData(message, unit_type)
        header = EISCPHeader(data_size=len(data.raw))
        return EISCPPacket(header, data)

    @cached_property
    def raw(self) -> bytes:
        """Serialize the eISCP packet."""
        return self.header.raw + self.iscp.raw

    @property
    def size(self) -> int:
        """Total size of the packet."""
        return self.header.total_size


class OnkyoHeaderError(OnkyoParsingError):
    """Onkyo header parsing error."""


@dataclass(kw_only=True)
class EISCPHeader:
    """eISCP header."""

    basic_length: ClassVar[int] = 16

    header_size: int = basic_length
    data_size: int
    version: int = 1
    reserved: bytes = b"\x00\x00\x00"
    additional: bytes | None = None

    _struct: ClassVar[struct.Struct] = struct.Struct("! 4s I I B 3s")

    @classmethod
    def parse(cls, header_plus: bytes) -> Self:
        """Parse the eISCP header."""
        if len(header_plus) < cls.basic_length:
            raise OnkyoHeaderError(
                f"Way too short eISCP header: {len(header_plus)} < {cls.basic_length}.\n"
                f"Header plus: {header_plus!r}"
            )
        header_basic = header_plus[: cls.basic_length]
        self = cls._parse_basic(header_basic)
        if self.header_size > cls.basic_length:
            if len(header_plus) < self.header_size:
                raise OnkyoHeaderError(
                    f"Too short eISCP header: {len(header_plus)} < {self.header_size}.\n"
                    f"Header plus: {header_plus!r}"
                )
            self.additional = header_plus[cls.basic_length : self.header_size]
        return self

    @classmethod
    async def parse_read(cls, reader: asyncio.StreamReader) -> Self:
        """Parse the eISCP header from reader."""
        basic = await reader.readexactly(cls.basic_length)
        self = cls._parse_basic(basic)
        additional_size = self.header_size - cls.basic_length
        if additional_size:
            self.additional = await reader.readexactly(additional_size)
        return self

    @classmethod
    def _parse_basic(cls, header: bytes) -> Self:
        """Parse the eISCP basic header."""
        try:
            unpacked = cls._struct.unpack(header)
        except struct.error as exc:
            raise OnkyoHeaderError(
                f"Invalid eISCP header structure: {exc!r}.\n"  # str-sep
                f"Header basic: {header!r}"
            ) from None
        magic, header_size, data_size, version, reserved = unpacked

        if magic != b"ISCP":
            raise OnkyoHeaderError(
                f"Invalid eISCP header magic: {magic}.\n"  # str-sep
                f"Header basic: {header!r}"
            )

        return cls(
            header_size=header_size,
            data_size=data_size,
            version=version,
            reserved=reserved,
        )

    @cached_property
    def raw(self) -> bytes:
        """Serialize the eISCP header."""
        packed_basic = self._struct.pack(
            b"ISCP", self.header_size, self.data_size, self.version, self.reserved
        )
        if self.additional is None:
            return packed_basic
        return packed_basic + self.additional

    @cached_property
    def total_size(self) -> int:
        """Get the total size of the header and data."""
        return self.header_size + self.data_size


class UnitType(Enum):
    """Unit type."""

    RECEIVER = b"1"
    DISCOVERY = b"x"
    PIONEER_DISCOVERY = b"p"


@dataclass
class ISCPData[M: Message]:
    """ISCP data."""

    message: M
    unit_type: UnitType
    end: bytes

    @cached_property
    def raw(self) -> bytes:
        """Serialize the ISCP data."""
        # Start character is "!"
        return b"!" + self.unit_type.value + self.message.raw + self.end


class OnkyoISCPDataError(OnkyoParsingError, OnkyoStreamRecoverableError):
    """Onkyo ISCP data parsing error."""


class OnkyoISCPMessageError(OnkyoISCPDataError):
    """Onkyo ISCP message parsing error."""

    raw_status: RawStatus

    def __init__(self, reason: str, raw_status: RawStatus) -> None:
        """Initialize."""
        super().__init__(f"{reason} Raw: {raw_status}")
        self.raw_status = raw_status


@dataclass
class ISCPStatusData(ISCPData[Status]):
    """ISCP status data."""

    @classmethod
    def parse(cls, data: bytes, *, parse_mode: ParseMode = ParseMode.EISCP) -> Self:
        """Parse the ISCP status data."""
        if data[0:1] != b"!":
            raise OnkyoISCPDataError(
                f"Invalid ISCP start: {data[0:1]!r}.\n"  # str-sep
                f"Data: {data!r}"
            )

        end = cls._parse_end(data, parse_mode)
        message_end = -len(end)

        try:
            unit_type = UnitType(data[1:2])
        except ValueError:
            raise OnkyoISCPDataError(
                f"Unknown ISCP unit type: {data[1:2]!r}.\n"  # str-sep
                f"Data: {data!r}"
            ) from None

        message_start = 2
        split = message_start + 3  # 3 is the code size
        code, parameter = data[message_start:split], data[split:message_end]
        message = cls._parse_message(code, parameter)

        return cls(message, unit_type, end)

    @staticmethod
    def _parse_end(data: bytes, parse_mode: ParseMode) -> bytes:
        """Parse the ISCP end characters."""
        ends: tuple[bytes, ...]
        match parse_mode:
            case ParseMode.ISCP:
                ends = (b"\x1a",)  # EOF (SUB)
            case ParseMode.EISCP:
                ends = (
                    b"\x1a\r\n",  # EOF (SUB) followed by CR+LF
                    b"\r\n",  # CR+LF ; example: b'!1TUN\r\n'
                )
            case ParseMode.DISCOVERY:
                ends = (b"\x19\r\n",)  # EOM followed by CR+LF

        for end in ends:
            if data.endswith(end):
                break
        else:
            raise OnkyoISCPDataError(
                f"Invalid ISCP end: ...{data[-5:]!r}. Parse mode: {parse_mode}.\n"  # str-sep
                f"Data: {data!r}"
            )

        return end

    @staticmethod
    def _parse_message(raw_code: bytes, parameter: bytes) -> Status:
        """Parse the ISCP status message."""
        code = Code.parse(raw_code)
        if code is None:
            return RawStatus(raw_code, parameter)
        status_cls = status_classes.get(code.kind)
        if status_cls is None:
            raw_status = RawStatus(raw_code, parameter)
            raise OnkyoISCPMessageError("ISCP message with no matching class.", raw_status)
        if parameter == b"N/A":
            return NotAvailableStatus.parse(code, parameter)
        try:
            status = status_cls.parse(code, parameter)
        except ValueError as exc:
            raw_status = RawStatus(raw_code, parameter)
            raise OnkyoISCPMessageError(
                f"ISCP message that couldn't be parsed ({exc}).", raw_status
            ) from None
        except Exception as exc:
            raw_status = RawStatus(raw_code, parameter)
            raise OnkyoISCPMessageError(
                f"¡ISCP message that couldn't be parsed a lot! ({exc!r})", raw_status
            ) from exc
        return status


@dataclass
class ISCPInstructionData(ISCPData[Instruction]):
    """ISCP instruction data."""

    unit_type: UnitType = UnitType.RECEIVER
    end: bytes = b"\r\n"  # End characters may be CR, LF or CR+LF


def _validate_status_packet(packet: EISCPPacket[Status]) -> Status | None:
    """Validate eISCP status packet."""
    header = packet.header
    iscp = packet.iscp
    # Not erroring here, assuming backwards compatibility in the future
    if header.version != 1:
        _LOGGER.info(
            "Unexpected eISCP header version: %s.\n"  # str-sep
            "Packet: %s",
            header.version,
            packet,
        )
    if header.header_size != EISCPHeader.basic_length:
        _LOGGER.info(
            "Unexpected eISCP header size : %s.\n"  # str-sep
            "Packet: %s",
            header.header_size,
            packet,
        )
    if header.reserved != b"\x00\x00\x00":
        _LOGGER.info(
            "Unexpected eISCP header reserved: %r.\n"  # str-sep
            "Packet: %s",
            header.reserved,
            packet,
        )
    if iscp.unit_type != UnitType.RECEIVER:
        _LOGGER.info(
            "Unexpected eISCP unit type: %s.\n"  # str-sep
            "Packet: %s",
            iscp.unit_type,
            packet,
        )
        return None
    return packet.iscp.message


async def read_message(reader: asyncio.StreamReader) -> Status:
    """Read message."""
    while True:
        try:
            packet = await EISCPPacket.parse_status_read(reader)
        except (OSError, EOFError) as exc:
            raise OnkyoConnectionError(f"{exc!r}") from None
        except OnkyoStreamRecoverableError as exc:
            _LOGGER.error("Invalid response: %s(%s)", type(exc).__name__, exc)
            continue
        except OnkyoParsingError as exc:
            _LOGGER.error("Invalid response (unrecoverable): %s(%s)", type(exc).__name__, exc)
            raise
        except Exception:
            _LOGGER.exception("¡Very invalid response!")
            raise
        message = _validate_status_packet(packet)
        if message is None:
            continue
        return message


async def write_message(writer: asyncio.StreamWriter, message: Instruction) -> None:
    """Write message."""
    packet = EISCPPacket.from_instruction_message(message)
    try:
        writer.write(packet.raw)
        await writer.drain()
    except OSError as exc:
        raise OnkyoConnectionError(f"{exc!r}") from None


async def read_messages(
    reader: asyncio.StreamReader, queue: asyncio.Queue[Status], info: BasicReceiverInfo
) -> None:
    """Read messages."""
    while True:
        message = await read_message(reader)
        _LOGGER.debug("[%s]   << %s", info.host, message)
        await queue.put(message)


async def write_messages(
    writer: asyncio.StreamWriter, queue: asyncio.Queue[Instruction], info: BasicReceiverInfo
) -> None:
    """Write messages."""
    while True:
        message = await queue.get()
        await write_message(writer, message)
        _LOGGER.debug("[%s] >>>> %s", info.host, message)


@dataclass(kw_only=True)
class DiscoveryInfo:
    """Discovery information."""

    ip: str
    port: int
    model_name: str
    iscp_port: int
    destination_area: DestinationArea
    identifier: str


@dataclass
class EISCPDiscovery(asyncio.DatagramProtocol):
    """eISCP Discovery Protocol."""

    target_str: str
    callback: Callable[[DiscoveryInfo], None]
    transport: asyncio.DatagramTransport | None = field(init=False, default=None)

    _discovered: set[str] = field(default_factory=set)

    packets: ClassVar[list[EISCPPacket[Instruction]]] = [
        EISCPPacket.from_instruction_message(DiscoveryQuery(), UnitType.DISCOVERY),
        EISCPPacket.from_instruction_message(DiscoveryQuery(), UnitType.PIONEER_DISCOVERY),
    ]

    def connection_made(
        self,
        transport: asyncio.DatagramTransport,  # type: ignore[override]
    ) -> None:
        """Send discovery packets after connection made."""
        self.transport = transport

        _LOGGER.debug("Sending discovery packets to %s", self.target_str)
        for packet in self.packets:
            self.transport.sendto(packet.raw)

    @staticmethod
    def _get_message(data: bytes) -> DiscoveryStatus | None:
        try:
            packet = EISCPPacket.parse_status(data, parse_mode=ParseMode.DISCOVERY)
        except OnkyoParsingError:
            _LOGGER.exception(
                "Invalid discovery response.\n"  # str-sep
                "Data: %s",
                data,
            )
            return None
        except Exception:
            _LOGGER.exception(
                "¡Very invalid discovery response!\n"  # str-sep
                "Data: %s",
                data,
            )
            return None
        message = _validate_status_packet(packet)
        if message is None:
            return None
        if not isinstance(message, DiscoveryStatus):
            _LOGGER.warning(
                "Invalid discovery response message type: %s\nPacket: %s",
                type(message).__name__,
                packet,
            )
            return None
        return message

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Parse and forward discovery info."""
        ip, port = addr
        _LOGGER.debug("Received discovery response from %s:%d", ip, port)

        message = self._get_message(data)
        if message is None:
            return

        if message.identifier in self._discovered:
            return
        self._discovered.add(message.identifier)

        discovery_info = DiscoveryInfo(
            ip=ip,
            port=port,
            model_name=message.model_name,
            iscp_port=message.iscp_port,
            destination_area=message.destination_area,
            identifier=message.identifier,
        )
        _LOGGER.debug("Discovery info: %s", discovery_info)

        self.callback(discovery_info)

    def close(self) -> None:
        """Close the discovery connection."""
        _LOGGER.debug("Closing the discovery connection %s", self.target_str)
        if self.transport is not None:
            self.transport.close()
