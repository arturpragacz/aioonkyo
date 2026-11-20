"""Instruction messages."""

from dataclasses import dataclass, field
from typing import ClassVar, TypeAlias, Unpack

from .message import CheckParamZonesMixin, KnownMessage, RawMessage, ValidateKwargs
from .message_code import Kind, Zone
from .parameter import (
    HDMIOutputParam,
    InputSourceParam,
    ListeningModeParam,
    MutingParam,
    NetJacketArtParam,
    NetOperationParam,
    ParamEnum,
    PowerParam,
    ToneParam,
    TunerPresetParam,
    TVOperationParam,
    VolumeParamEnum,
    VolumeParamNumeric,
)


@dataclass
class _Instruction(KnownMessage):
    zone: Zone = field()

    # _validate needs to be called by each subclass
    def _validate(self, **kwargs: Unpack[ValidateKwargs]) -> None:
        try:
            _ = self.code
        except KeyError:
            raise ValueError(f"Invalid zone {self.zone} for {self.__class__.__name__}") from None
        super()._validate(**kwargs)


@dataclass
class _MainZoneInstructionMixin:
    # cannot be a ClassVar because mypy complains
    # mypy - 'error: Missing positional argument "zone" in call'
    zone: Zone = field(init=False, repr=False, default=Zone.MAIN)


@dataclass
class _Query(_Instruction):
    parameter: bytes = field(init=False, repr=False, default=b"QSTN")

    def __post_init__(self) -> None:
        self._validate()


@dataclass
class PowerQuery(_Query):
    kind: ClassVar[Kind] = Kind.POWER


@dataclass
class MutingQuery(_Query):
    kind: ClassVar[Kind] = Kind.MUTING


@dataclass
class ChannelMutingQuery(_MainZoneInstructionMixin, _Query):
    kind: ClassVar[Kind] = Kind.CHANNEL_MUTING


@dataclass
class VolumeQuery(_Query):
    kind: ClassVar[Kind] = Kind.VOLUME


@dataclass
class ToneQuery(_Query):
    kind: ClassVar[Kind] = Kind.TONE


@dataclass
class InputSourceQuery(_Query):
    kind: ClassVar[Kind] = Kind.INPUT_SOURCE


@dataclass
class ListeningModeQuery(_Query):
    kind: ClassVar[Kind] = Kind.LISTENING_MODE


@dataclass
class HDMIOutputQuery(_MainZoneInstructionMixin, _Query):
    kind: ClassVar[Kind] = Kind.HDMI_OUTPUT


@dataclass
class AudioInformationQuery(_MainZoneInstructionMixin, _Query):
    kind: ClassVar[Kind] = Kind.AUDIO_INFORMATION


@dataclass
class VideoInformationQuery(_MainZoneInstructionMixin, _Query):
    kind: ClassVar[Kind] = Kind.VIDEO_INFORMATION


@dataclass
class TunerPresetQuery(_Query):
    kind: ClassVar[Kind] = Kind.TUNER_PRESET


@dataclass
class FLDisplayQuery(_MainZoneInstructionMixin, _Query):
    kind: ClassVar[Kind] = Kind.FL_DISPLAY


@dataclass
class TemperatureQuery(_MainZoneInstructionMixin, _Query):
    kind: ClassVar[Kind] = Kind.TEMPERATURE


@dataclass
class DiscoveryQuery(_MainZoneInstructionMixin, _Query):
    kind: ClassVar[Kind] = Kind.DISCOVERY


@dataclass
class NetPlayStatusQuery(_MainZoneInstructionMixin, _Query):
    kind: ClassVar[Kind] = Kind.NET_PLAY_STATUS


@dataclass
class NetTitleQuery(_MainZoneInstructionMixin, _Query):
    kind: ClassVar[Kind] = Kind.NET_TITLE


@dataclass
class NetArtistQuery(_MainZoneInstructionMixin, _Query):
    kind: ClassVar[Kind] = Kind.NET_ARTIST


@dataclass
class NetAlbumQuery(_MainZoneInstructionMixin, _Query):
    kind: ClassVar[Kind] = Kind.NET_ALBUM


@dataclass
class NetTimeQuery(_MainZoneInstructionMixin, _Query):
    kind: ClassVar[Kind] = Kind.NET_TIME


@dataclass
class NetTrackQuery(_MainZoneInstructionMixin, _Query):
    kind: ClassVar[Kind] = Kind.NET_TRACK


@dataclass
class NetMenuQuery(_MainZoneInstructionMixin, _Query):
    kind: ClassVar[Kind] = Kind.NET_MENU


@dataclass
class NetJacketArtQuery(_MainZoneInstructionMixin, _Query):
    """Query the jacket art mode; NetJacketArtCommand requests the art itself."""

    kind: ClassVar[Kind] = Kind.NET_JACKET_ART


@dataclass
class _ParamCommand[ParamT: ParamEnum](_Instruction):
    kind: ClassVar[Kind]

    param: ParamT

    parameter: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.parameter = self.param.raw
        self._validate(param=self.param)


class PowerCommand(_ParamCommand[PowerParam]):
    kind: ClassVar[Kind] = Kind.POWER
    Param: TypeAlias = PowerParam


class MutingCommand(_ParamCommand[MutingParam]):
    kind: ClassVar[Kind] = Kind.MUTING
    Param: TypeAlias = MutingParam


class InputSourceCommand(CheckParamZonesMixin, _ParamCommand[InputSourceParam]):
    kind: ClassVar[Kind] = Kind.INPUT_SOURCE
    Param: TypeAlias = InputSourceParam


class ListeningModeCommand(CheckParamZonesMixin, _ParamCommand[ListeningModeParam]):
    kind: ClassVar[Kind] = Kind.LISTENING_MODE
    Param: TypeAlias = ListeningModeParam


# needs to be a dataclass because it inherits from two dataclasses
@dataclass
class _HDMIOutputCommand(_MainZoneInstructionMixin, _ParamCommand[HDMIOutputParam]):
    kind: ClassVar[Kind] = Kind.HDMI_OUTPUT


class HDMIOutputCommand(_HDMIOutputCommand):
    # TypeAlias doesn't work in dataclasses
    Param: TypeAlias = HDMIOutputParam


# needs to be a dataclass because it inherits from two dataclasses
@dataclass
class _TVOperationCommand(_MainZoneInstructionMixin, _ParamCommand[TVOperationParam]):
    kind: ClassVar[Kind] = Kind.TV_OPERATION


class TVOperationCommand(_TVOperationCommand):
    # TypeAlias doesn't work in dataclasses
    Param: TypeAlias = TVOperationParam


@dataclass
class _NetOperationCommand(_MainZoneInstructionMixin, _ParamCommand[NetOperationParam]):
    kind: ClassVar[Kind] = Kind.NET_OPERATION


class NetOperationCommand(_NetOperationCommand):
    Param: TypeAlias = NetOperationParam


@dataclass
class _NetJacketArtCommand(_MainZoneInstructionMixin, _ParamCommand[NetJacketArtParam]):
    kind: ClassVar[Kind] = Kind.NET_JACKET_ART


class NetJacketArtCommand(_NetJacketArtCommand):
    """Set the jacket art mode, or request the current track's jacket art."""

    Param: TypeAlias = NetJacketArtParam


# NTS takes hh:mm:ss, or mm:ss on players without an hours field.
_NET_TIME_SEEK_MAX = 99 * 3600 + 59 * 60 + 59
_NET_TIME_SEEK_MAX_SHORT = 99 * 60 + 59


@dataclass
class NetTimeSeekCommand(_MainZoneInstructionMixin, _Instruction):
    """Seek the network player, in whole seconds.

    Receivers accept it only while NMS reports Time Seek as enabled. The position is sent as
    hh:mm:ss; pass `hours=False` for players that use the older mm:ss form, up to 99:59.
    """

    kind: ClassVar[Kind] = Kind.NET_TIME_SEEK

    position: int
    hours: bool = field(default=True, kw_only=True)

    parameter: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        maximum = _NET_TIME_SEEK_MAX if self.hours else _NET_TIME_SEEK_MAX_SHORT
        if not 0 <= self.position <= maximum:
            raise ValueError(f"Position {self.position} out of range for {self.__class__.__name__}")
        minutes, seconds = divmod(self.position, 60)
        if self.hours:
            hours, minutes = divmod(minutes, 60)
            self.parameter = f"{hours:02}:{minutes:02}:{seconds:02}".encode()
        else:
            self.parameter = f"{minutes:02}:{seconds:02}".encode()
        self._validate()


@dataclass
class _VolumeCommand(_Instruction):
    kind: ClassVar[Kind] = Kind.VOLUME

    param: VolumeParamEnum | int

    parameter: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.param, VolumeParamEnum):
            self.parameter = self.param.raw
            self._validate(param=self.param)
            return

        self.parameter = VolumeParamNumeric.from_numeric(self.param).raw
        self._validate()


class VolumeCommand(_VolumeCommand):
    # TypeAlias doesn't work in dataclasses
    Param: TypeAlias = VolumeParamEnum


@dataclass
class TunerPresetCommand(_Instruction):
    kind: ClassVar[Kind] = Kind.TUNER_PRESET

    param: int

    parameter: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.parameter = TunerPresetParam.from_numeric(self.param).raw
        self._validate()


@dataclass(kw_only=True)
class ToneCommand(_Instruction):
    kind: ClassVar[Kind] = Kind.TONE

    bass: int | None = None
    treble: int | None = None

    parameter: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (self.bass is None and self.treble is None) or (
            self.bass is not None and self.treble is not None
        ):
            raise ValueError(
                f"Exactly one of bass or treble must be set for {self.__class__.__name__}"
            )

        if self.bass is not None:
            self.parameter = b"B" + ToneParam.from_numeric(self.bass).raw

        if self.treble is not None:
            self.parameter = b"T" + ToneParam.from_numeric(self.treble).raw

        self._validate()


# needs to be a dataclass because it inherits from two dataclasses
@dataclass(kw_only=True)
class _ChannelMutingCommand(_MainZoneInstructionMixin, _Instruction):
    kind: ClassVar[Kind] = Kind.CHANNEL_MUTING

    front_left: MutingParam = MutingParam.OFF
    front_right: MutingParam = MutingParam.OFF
    center: MutingParam = MutingParam.OFF
    surround_left: MutingParam = MutingParam.OFF
    surround_right: MutingParam = MutingParam.OFF
    surround_back_left: MutingParam = MutingParam.OFF
    surround_back_right: MutingParam = MutingParam.OFF
    subwoofer: MutingParam = MutingParam.OFF
    height_1_left: MutingParam = MutingParam.OFF
    height_1_right: MutingParam = MutingParam.OFF
    height_2_left: MutingParam = MutingParam.OFF
    height_2_right: MutingParam = MutingParam.OFF
    subwoofer_2: MutingParam = MutingParam.OFF

    parameter: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.parameter = b"".join(
            param.raw for param in vars(self).values() if isinstance(param, MutingParam)
        )
        self._validate()


class ChannelMutingCommand(_ChannelMutingCommand):
    # TypeAlias doesn't work in dataclasses
    Param: TypeAlias = MutingParam


type KnownQuery = (
    PowerQuery
    | MutingQuery
    | ChannelMutingQuery
    | VolumeQuery
    | ToneQuery
    | InputSourceQuery
    | ListeningModeQuery
    | HDMIOutputQuery
    | AudioInformationQuery
    | VideoInformationQuery
    | TunerPresetQuery
    | FLDisplayQuery
    | TemperatureQuery
    | DiscoveryQuery
    | NetPlayStatusQuery
    | NetTitleQuery
    | NetArtistQuery
    | NetAlbumQuery
    | NetTimeQuery
    | NetTrackQuery
    | NetMenuQuery
    | NetJacketArtQuery
)

type KnownCommand = (
    PowerCommand
    | MutingCommand
    | InputSourceCommand
    | ListeningModeCommand
    | HDMIOutputCommand
    | TVOperationCommand
    | NetOperationCommand
    | NetJacketArtCommand
    | NetTimeSeekCommand
    | VolumeCommand
    | TunerPresetCommand
    | ToneCommand
    | ChannelMutingCommand
)

type KnownInstruction = KnownQuery | KnownCommand


class RawInstruction(RawMessage):
    pass


type Instruction = KnownInstruction | RawInstruction
