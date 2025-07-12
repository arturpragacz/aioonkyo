"""Messages."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, ClassVar, Self


class Zone(Enum):
    MAIN = "main"
    ZONE1 = MAIN
    ZONE2 = "zone2"
    ZONE3 = "zone3"
    ZONE4 = "zone4"

    def __repr__(self) -> str:
        return str(self)


ALL_ZONES = (Zone.MAIN, Zone.ZONE2, Zone.ZONE3, Zone.ZONE4)


class Kind(Enum):
    POWER = auto()
    MUTING = auto()
    CHANNEL_MUTING = auto()
    VOLUME = auto()
    TONE = auto()
    INPUT_SOURCE = auto()
    LISTENING_MODE = auto()
    HDMI_OUTPUT = auto()
    AUDIO_INFORMATION = auto()
    VIDEO_INFORMATION = auto()
    TUNER_PRESET = auto()
    FL_DISPLAY = auto()
    DISCOVERY = auto()

    def __repr__(self) -> str:
        return str(self)


@dataclass(slots=True, init=False)
class _CodeBaseConcreteMixin:
    kind: Kind
    zone: Zone
    raw: bytes = field(repr=False, init=False)

    def __new__(cls, kind: Kind, zone: Zone) -> Self:
        self = object.__new__(cls)
        self.kind = kind
        self.zone = zone
        return self

    @property
    def value(self) -> _CodeBaseConcreteMixin:
        """Code value."""
        # only for typing, this function is actually removed
        return self


del _CodeBaseConcreteMixin.value


# should be _CodeBase, but then the class vars don't work with Enum properly
class CodeBase(_CodeBaseConcreteMixin, Enum):
    __kind_mapping: ClassVar[dict[Kind, dict[Zone, Code]]] = {}
    __raw_mapping: ClassVar[dict[bytes, Code]] = {}

    def __init__(self, kind: Kind, zone: Zone) -> None:
        if TYPE_CHECKING:
            assert isinstance(self, Code)
        raw = self.name.encode()
        self.value.raw = self.raw = raw
        self.__kind_mapping.setdefault(kind, {})[zone] = self
        self.__raw_mapping[raw] = self

    @classmethod
    def from_kind_zone(cls, kind: Kind, zone: Zone) -> Code:
        return cls.__kind_mapping[kind][zone]

    @classmethod
    def get_from_kind_zone(cls, kind: Kind, zone: Zone) -> Code | None:
        return cls.__kind_mapping[kind].get(zone)

    @classmethod
    def parse(cls, raw_code: bytes) -> Code | None:
        return cls.__raw_mapping.get(raw_code)


class Code(CodeBase):
    # POWER
    PWR = Kind.POWER, Zone.MAIN
    ZPW = Kind.POWER, Zone.ZONE2
    PW3 = Kind.POWER, Zone.ZONE3
    PW4 = Kind.POWER, Zone.ZONE4
    # MUTING
    AMT = Kind.MUTING, Zone.MAIN
    ZMT = Kind.MUTING, Zone.ZONE2
    MT3 = Kind.MUTING, Zone.ZONE3
    MT4 = Kind.MUTING, Zone.ZONE4
    # CHANNEL MUTING
    CMT = Kind.CHANNEL_MUTING, Zone.MAIN
    # VOLUME
    MVL = Kind.VOLUME, Zone.MAIN
    ZVL = Kind.VOLUME, Zone.ZONE2
    VL3 = Kind.VOLUME, Zone.ZONE3
    VL4 = Kind.VOLUME, Zone.ZONE4
    # TONE
    TFR = Kind.TONE, Zone.MAIN
    ZTN = Kind.TONE, Zone.ZONE2
    TN3 = Kind.TONE, Zone.ZONE3
    # INPUT SOURCE
    SLI = Kind.INPUT_SOURCE, Zone.MAIN
    SLZ = Kind.INPUT_SOURCE, Zone.ZONE2
    SL3 = Kind.INPUT_SOURCE, Zone.ZONE3
    SL4 = Kind.INPUT_SOURCE, Zone.ZONE4
    # LISTENING MODE
    LMD = Kind.LISTENING_MODE, Zone.MAIN
    LMZ = Kind.LISTENING_MODE, Zone.ZONE2
    # HDMI OUTPUT
    HDO = Kind.HDMI_OUTPUT, Zone.MAIN
    # AUDIO INFORMATION
    IFA = Kind.AUDIO_INFORMATION, Zone.MAIN
    # VIDEO INFORMATION
    IFV = Kind.VIDEO_INFORMATION, Zone.MAIN
    # TUNER PRESET
    PRS = Kind.TUNER_PRESET, Zone.MAIN
    PRZ = Kind.TUNER_PRESET, Zone.ZONE2
    PR3 = Kind.TUNER_PRESET, Zone.ZONE3
    PR4 = Kind.TUNER_PRESET, Zone.ZONE4
    # FL DISPLAY
    FLD = Kind.FL_DISPLAY, Zone.MAIN
    # DISCOVERY
    ECN = Kind.DISCOVERY, Zone.MAIN


__all__ = [
    "Zone",
    "Kind",
    "Code",
]
