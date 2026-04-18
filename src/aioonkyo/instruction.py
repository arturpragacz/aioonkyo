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
    ParamEnum,
    PowerParam,
    ToneParam,
    TunerPresetParam,
    TVOperationParam,
    VolumeParamEnum,
    VolumeParamNumeric,
    TemporaryChannelLevelNumeric,
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
class TemporaryChannelLevelQuery(_MainZoneInstructionMixin, _Query):
    kind: ClassVar[Kind] = Kind.TEMPORARY_CHANNEL_LEVEL


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


# needs to be a dataclass because it inherits from two dataclasses
@dataclass(kw_only=True)
class _TemporaryChannelLevelCommand(_MainZoneInstructionMixin, _Instruction):
    kind: ClassVar[Kind] = Kind.TEMPORARY_CHANNEL_LEVEL
    # Each channel is represented as a simple int in range [-16, 16].
    # The dataclass contains one attribute per channel (default 0).
    front_left: int = 0
    front_right: int = 0
    center: int = 0
    surround_left: int = 0
    surround_right: int = 0
    surround_back_left: int = 0
    surround_back_right: int = 0
    subwoofer: int = 0
    height_1_left: int = 0
    height_1_right: int = 0
    height_2_left: int = 0
    height_2_right: int = 0
    subwoofer_2: int = 0

    parameter: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        parts: list[bytes] = []
        for param, val in vars(self).items():
            if isinstance(val, Kind):
                continue
            if not isinstance(val, int):
                raise TypeError(f"Channel {param} must be int, got {type(val).__name__}")
            # encode single int to 3-char ASCII using helper
            enc = TemporaryChannelLevelNumeric.from_numeric(val)
            parts.append(enc.raw)

        self.parameter = b"".join(parts)
        self._validate()


class TemporaryChannelLevelCommand(_TemporaryChannelLevelCommand):
    # TypeAlias doesn't work in dataclasses
    Param: TypeAlias = int


type KnownQuery = (
    PowerQuery
    | MutingQuery
    | ChannelMutingQuery
    | TemporaryChannelLevelQuery
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
)

type KnownCommand = (
    PowerCommand
    | MutingCommand
    | InputSourceCommand
    | ListeningModeCommand
    | HDMIOutputCommand
    | TVOperationCommand
    | VolumeCommand
    | TunerPresetCommand
    | ToneCommand
    | ChannelMutingCommand
    | TemporaryChannelLevelCommand
)

type KnownInstruction = KnownQuery | KnownCommand


class RawInstruction(RawMessage):
    pass


type Instruction = KnownInstruction | RawInstruction
