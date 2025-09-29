"""Status messages."""

from collections.abc import Iterable
from dataclasses import dataclass, field
import re
import typing
from typing import ClassVar, Self, TypeAlias

from .message import CheckParamZonesMixin, KnownMessage, RawMessage
from .message_code import Code, Kind, Zone
from .parameter import (
    DestinationArea,
    HDMIOutputParam,
    InputSourceParam,
    ListeningModeParam,
    MutingParam,
    ParamEnum,
    ParamNumeric,
    PowerParam,
    TemperatureParam,
    ToneParam,
    TunerPresetParam,
    VolumeParamNumeric,
)


@dataclass
class _KnownStatus(KnownMessage):
    zone: Zone = field(init=False)  # actual implementation in super class, here only for repr
    code: Code = field(repr=False)
    parameter: bytes = field(repr=False)


@dataclass
class _ParamStatus[ParamT: ParamEnum](_KnownStatus):
    kind: ClassVar[Kind]

    Param: ClassVar[type[ParamT]]  # type: ignore[misc] # "ClassVar cannot contain type variables"
    param: ParamT

    __match_args__ = ("param",)

    @classmethod
    def parse(cls, code: Code, parameter: bytes) -> Self:
        param = cls.Param.parse(parameter)
        self = cls(code, parameter, param)
        self._validate(param=param)
        return self


class PowerStatus(_ParamStatus[PowerParam]):
    kind: ClassVar[Kind] = Kind.POWER
    Param: TypeAlias = PowerParam


class MutingStatus(_ParamStatus[MutingParam]):
    kind: ClassVar[Kind] = Kind.MUTING
    Param: TypeAlias = MutingParam


class InputSourceStatus(CheckParamZonesMixin, _ParamStatus[InputSourceParam]):
    kind: ClassVar[Kind] = Kind.INPUT_SOURCE
    Param: TypeAlias = InputSourceParam


class ListeningModeStatus(CheckParamZonesMixin, _ParamStatus[ListeningModeParam]):
    kind: ClassVar[Kind] = Kind.LISTENING_MODE
    Param: TypeAlias = ListeningModeParam


class HDMIOutputStatus(_ParamStatus[HDMIOutputParam]):
    kind: ClassVar[Kind] = Kind.HDMI_OUTPUT
    Param: TypeAlias = HDMIOutputParam


@dataclass
class _NumericStatus(_KnownStatus):
    kind: ClassVar[Kind]

    Param: ClassVar[ParamNumeric]
    param: int

    __match_args__ = ("param",)

    @classmethod
    def parse(cls, code: Code, parameter: bytes) -> Self:
        param = cls.Param.parse(parameter)
        self = cls(code, parameter, param)
        self._validate()
        return self


class VolumeStatus(_NumericStatus):
    kind: ClassVar[Kind] = Kind.VOLUME
    Param: TypeAlias = VolumeParamNumeric


@dataclass
class TemperatureStatus(_KnownStatus):
    kind: ClassVar[Kind] = Kind.TEMPERATURE

    celsius: int

    __match_args__ = ("celsius",)

    _regex: ClassVar[re.Pattern[bytes]] = re.compile(rb"F.+C(?P<celsius>.+)")

    @classmethod
    def parse(cls, code: Code, parameter: bytes) -> Self:
        match = cls._regex.fullmatch(parameter)

        if match is None:
            raise ValueError(f"Regex match fail in {cls.__name__}")

        celsius = TemperatureParam.parse(match["celsius"])

        self = cls(code, parameter, celsius)
        self._validate()
        return self


class TunerPresetStatus(_NumericStatus):
    kind: ClassVar[Kind] = Kind.TUNER_PRESET
    Param: TypeAlias = TunerPresetParam


@dataclass
class _ToneStatus(_KnownStatus):
    kind: ClassVar[Kind] = Kind.TONE

    bass: int
    treble: int

    __match_args__ = ("bass", "treble")

    _regex: ClassVar[re.Pattern[bytes]] = re.compile(rb"B(?P<bass>.+?)T(?P<treble>.+)")

    @classmethod
    def parse(cls, code: Code, parameter: bytes) -> Self:
        match = cls._regex.fullmatch(parameter)

        if match is None:
            raise ValueError(f"Regex match fail in {cls.__name__}")

        bass = ToneParam.parse(match["bass"])
        treble = ToneParam.parse(match["treble"])

        self = cls(code, parameter, bass, treble)
        self._validate()
        return self


class ToneStatus(_ToneStatus):
    # TypeAlias doesn't work in dataclasses
    Param: TypeAlias = ToneParam


@dataclass(match_args=False)
class _ChannelMutingStatus(_KnownStatus):
    kind: ClassVar[Kind] = Kind.CHANNEL_MUTING

    front_left: MutingParam
    front_right: MutingParam
    center: MutingParam
    surround_left: MutingParam
    surround_right: MutingParam
    surround_back_left: MutingParam
    surround_back_right: MutingParam
    subwoofer: MutingParam
    height_1_left: MutingParam
    height_1_right: MutingParam
    height_2_left: MutingParam
    height_2_right: MutingParam
    subwoofer_2: MutingParam

    @classmethod
    def parse(cls, code: Code, parameter: bytes) -> Self:
        if len(parameter) != 13 * 2:
            raise ValueError(f"Incorrect number of values in {cls.__name__}")

        values = (MutingParam.parse(parameter[i : i + 2]) for i in range(0, len(parameter), 2))

        self = cls(code, parameter, *values)
        self._validate()
        return self


class ChannelMutingStatus(_ChannelMutingStatus):
    # TypeAlias doesn't work in dataclasses
    Param: TypeAlias = MutingParam


@dataclass(match_args=False)
class AudioInformationStatus(_KnownStatus):
    kind: ClassVar[Kind] = Kind.AUDIO_INFORMATION

    audio_input_port: str | None = None
    input_signal_format: str | None = None
    input_frequency: str | None = None
    input_channels: str | None = None
    listening_mode: str | None = None
    output_channels: str | None = None
    output_frequency: str | None = None
    precision_quartz_lock_system: str | None = None
    auto_phase_control_delay: str | None = None
    auto_phase_control_phase: str | None = None
    upmix_mode: str | None = None

    @classmethod
    def parse(cls, code: Code, parameter: bytes) -> Self:
        values = parameter.split(b",")

        if values[-1] != b"":
            raise ValueError(f"No trailing comma in {cls.__name__}")
        values = values[:-1]

        if len(values) == 0:
            raise ValueError(f"No values in {cls.__name__}")
        if len(values) > 11:
            raise ValueError(f"Too many values in {cls.__name__}")

        decoded_values = [value.decode() for value in values]
        self = cls(code, parameter, *decoded_values)
        self._validate()
        return self


@dataclass(match_args=False)
class VideoInformationStatus(_KnownStatus):
    kind: ClassVar[Kind] = Kind.VIDEO_INFORMATION

    video_input_port: str | None = None
    input_resolution: str | None = None
    input_color_schema: str | None = None
    input_color_depth: str | None = None
    video_output_port: str | None = None
    output_resolution: str | None = None
    output_color_schema: str | None = None
    output_color_depth: str | None = None
    picture_mode: str | None = None
    input_hdr: str | None = None

    @classmethod
    def parse(cls, code: Code, parameter: bytes) -> Self:
        values = parameter.split(b",")

        if values[-1] != b"":
            raise ValueError(f"No trailing comma in {cls.__name__}")
        values = values[:-1]

        if len(values) == 0:
            raise ValueError(f"No values in {cls.__name__}")
        if len(values) > 10:
            raise ValueError(f"Too many values in {cls.__name__}")

        decoded_values = [value.decode() for value in values]
        self = cls(code, parameter, *decoded_values)
        self._validate()
        return self


@dataclass
class FLDisplayStatus(_KnownStatus):
    kind: ClassVar[Kind] = Kind.FL_DISPLAY

    param: str

    __match_args__ = ("param",)

    _special_chars: ClassVar[dict[int, str]] = {
        0x08: "↑",
        0x09: "↓",
        0x0A: "←",
        0x0B: "→",
        0x12: "◗",  # Dolby Logo Left
        0x13: "◖",  # Dolby Logo Right
        # 0x14: "Ⅱ",  # "⏸"?
        # 0x15: "Ω",  # "⏹"?
        0x1A: "⏵",
        0x1B: "⏸",
        0x7F: "▮",  # Cursor
        0x80: "👤",  # Artist
        0x81: "🖸",  # Album
        0x82: "🗀",  # Folder
        0x83: "♫",  # Song
        0x84: "Tr̄",  # Track
        0x90: ".⁰",
        0x91: ".¹",
        0x92: ".²",
        0x93: ".³",
        0x94: ".⁴",
        0x95: ".⁵",
        0x96: ".⁶",
        0x97: ".⁷",
        0x98: ".⁸",
        0x99: ".⁹",
    }

    @classmethod
    def parse(cls, code: Code, parameter: bytes) -> Self:
        if len(parameter) % 2 != 0:
            raise ValueError(f"Odd number of characters {len(parameter)} in {cls.__name__}")

        pairs = (parameter[i : i + 2] for i in range(0, len(parameter), 2))

        special_chars = cls._special_chars

        def translate() -> Iterable[str]:
            for pair in pairs:
                pair_int = int(pair, 16)
                if 0x20 <= pair_int <= 0x7E or 0xA1 <= pair_int <= 0xFF:
                    yield chr(pair_int)
                elif pair_int in special_chars:
                    yield special_chars[pair_int]
                else:
                    raise ValueError(f"Invalid character {pair!r} in {cls.__name__}")

        text = "".join(translate())
        self = cls(code, parameter, text)
        self._validate()
        return self


@dataclass(match_args=False)
class DiscoveryStatus(_KnownStatus):
    kind: ClassVar[Kind] = Kind.DISCOVERY

    model_name: str
    iscp_port: int
    destination_area: DestinationArea
    identifier: str

    _regex: ClassVar[re.Pattern[bytes]] = re.compile(
        rb"""
            (?P<model_name>[^/]{1,64})/
            (?P<iscp_port>\d{5})/
            (?P<destination_area>[A-Z]{2})/
            (?P<identifier>.{1,12})
        """,
        re.VERBOSE,
    )

    @classmethod
    def parse(cls, code: Code, parameter: bytes) -> Self:
        match = cls._regex.fullmatch(parameter)

        if match is None:
            raise ValueError(f"Regex match fail in {cls.__name__}")

        self = cls(
            code=code,
            parameter=parameter,
            model_name=match["model_name"].decode(),
            iscp_port=int(match["iscp_port"]),
            destination_area=DestinationArea(match["destination_area"].decode()),
            identifier=match["identifier"].decode(),
        )
        self._validate()
        return self


@dataclass
class NotAvailableStatus(_KnownStatus):
    kind: Kind = field()

    __match_args__ = ("kind",)

    @classmethod
    def parse(cls, code: Code, parameter: bytes) -> Self:
        self = cls(code, parameter, code.kind)
        self._validate()
        return self


type ValidStatus = (
    PowerStatus
    | MutingStatus
    | InputSourceStatus
    | ListeningModeStatus
    | HDMIOutputStatus
    | VolumeStatus
    | TemperatureStatus
    | TunerPresetStatus
    | ToneStatus
    | ChannelMutingStatus
    | AudioInformationStatus
    | VideoInformationStatus
    | FLDisplayStatus
    | DiscoveryStatus
)

type KnownStatus = ValidStatus | NotAvailableStatus


class RawStatus(RawMessage):
    pass


type Status = KnownStatus | RawStatus


_status_classes_list: tuple[ValidStatus, ...] = typing.get_args(ValidStatus.__value__)
status_classes = {cls.kind: cls for cls in _status_classes_list}
