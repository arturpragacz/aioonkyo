"""Parameters."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from typing import Any, ClassVar, Final, Self, cast, overload

from .message_code import ALL_ZONES, Zone


class _ParamBase:
    """Base class for params, like ParamEnum or ParamNumeric."""

    @property
    def value(self) -> str:
        """Param value."""
        # only for typing, this function is actually removed
        return ""

    @cached_property
    def raw(self) -> bytes:
        """Param value in bytes form."""
        return self.value.encode()


del _ParamBase.value


class _ParamEnumBase(_ParamBase):
    meanings: tuple[str, ...] = ()
    all_meanings: tuple[str, ...] = ()
    zones: tuple[Zone, ...] = ()


@dataclass(slots=True)
class ParamEnumSettings:
    meanings: str | tuple[str, ...] = ()
    extra_meanings: str | tuple[str, ...] = field(kw_only=True, default=())
    zones: tuple[Zone, ...] | None = field(kw_only=True, default=None)


def _get_empty_zone_mapping() -> dict[Zone, set[Any]]:
    return {zone: set() for zone in ALL_ZONES}


_DEFAULT_ZONE_MAPPING = _get_empty_zone_mapping()

_DEFAULT_PARAM_ENUM_SETTINGS: Final = ParamEnumSettings()


class ParamEnum(_ParamEnumBase, Enum):
    # mypy - "Final name declared in class body cannot depend on type variables"
    __zone_mapping: ClassVar[dict[Zone, set[Self]]] = _DEFAULT_ZONE_MAPPING  # type: ignore[misc]

    def __new__(
        cls, value: str, _settings: ParamEnumSettings = _DEFAULT_PARAM_ENUM_SETTINGS, /
    ) -> Self:
        # Only use first argument as the Enum value
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    # Empty overload init below to provide proper signature to mypy.
    # It is necessary, becauese mypy does not understand Enum __new__ magic.
    @overload  # type: ignore[misc] # mypy - "Single overload definition, multiple required"
    def __init__(self, value: str, /) -> None: ...

    def __init__(
        self, value: str, settings: ParamEnumSettings = _DEFAULT_PARAM_ENUM_SETTINGS, /
    ) -> None:
        meanings = settings.meanings
        extra_meanings = settings.extra_meanings
        zones = settings.zones
        if zones is None:
            zones = self._default_settings_zones()
        if isinstance(meanings, str):
            meanings = (meanings,)
        if isinstance(extra_meanings, str):
            extra_meanings = (extra_meanings,)

        # _value2member_map_ is undocumented
        canonical = cast(ParamEnum | None, self._value2member_map_.get(value))  # type: ignore[attr-defined]
        if canonical is not None:
            canonical.meanings = (*canonical.meanings, *meanings)
            canonical.all_meanings = (*canonical.all_meanings, *meanings, *extra_meanings)
            return

        # canonical does not yet exist, so it means we are canonical

        if not meanings:
            meanings = (self.name.replace("_", " "),)
        self.meanings = meanings
        self.all_meanings = (*meanings, *extra_meanings)

        if not zones:
            return

        self.zones = zones
        if self.__zone_mapping is _DEFAULT_ZONE_MAPPING:
            # mypy - 'Cannot assign to final attribute "__zone_mapping"'
            type(self).__zone_mapping = _get_empty_zone_mapping()  # type: ignore[misc] # noqa: SLF001
        for zone in self.zones:
            # mypy - 'Argument 1 to "add" of "set" has incompatible type "ParamEnum"; expected "Self"'
            self.__zone_mapping[zone].add(self)  # type: ignore[arg-type]

    @classmethod
    def _default_settings_zones(cls) -> tuple[Zone, ...]:
        return ALL_ZONES

    @classmethod
    def for_zone(cls, zone: Zone) -> set[Self]:
        return cls.__zone_mapping[zone]

    @classmethod
    def parse(cls, parameter: bytes) -> Self:
        return cls(parameter.decode())


class MainZoneParamEnum(ParamEnum):
    @classmethod
    def _default_settings_zones(cls) -> tuple[Zone, ...]:
        return (Zone.MAIN,)


class PowerParam(ParamEnum):
    STANDBY = "00"
    ON = "01"
    # ALL_STANDBY = "ALL", ParamEnumSettings(zones=(Zone.MAIN,))


class MutingParam(ParamEnum):
    OFF = "00"
    ON = "01"


class VolumeParamEnum(ParamEnum):
    UP = "UP"
    DOWN = "DOWN"
    UP1 = "UP1", ParamEnumSettings("UP 1")
    DOWN1 = "DOWN1", ParamEnumSettings("DOWN 1")


class InputSourceParam(ParamEnum):
    VIDEO1_DVR_VCR_STB = "00", ParamEnumSettings(("VIDEO1", "VCR/DVR", "STB/DVR"))
    VIDEO1 = DVR = VCR = STB = VIDEO1_DVR_VCR_STB[0]
    VIDEO2_CBL_SAT = "01", ParamEnumSettings(("VIDEO2", "CBL/SAT"))
    VIDEO2 = CBL = SAT = VIDEO2_CBL_SAT[0]
    VIDEO3_GAME = "02", ParamEnumSettings(("VIDEO3", "GAME/TV", "GAME"))
    VIDEO3 = GAME = VIDEO3_GAME[0]
    VIDEO4_AUX = "03", ParamEnumSettings(("VIDEO4", "AUX"))
    VIDEO4 = AUX = VIDEO4_AUX[0]
    VIDEO5_GAME2_AUX2 = "04", ParamEnumSettings(("VIDEO5", "AUX2", "GAME2"))
    VIDEO5 = GAME2 = AUX2 = VIDEO5_GAME2_AUX2[0]
    VIDEO6_PC = "05", ParamEnumSettings(("VIDEO6", "PC"))
    VIDEO6 = PC = VIDEO6_PC[0]
    VIDEO7 = "06"
    HIDDEN1_EXTRA1 = "07", ParamEnumSettings(("HIDDEN1", "EXTRA1"))
    HIDDEN2_EXTRA2 = "08", ParamEnumSettings(("HIDDEN2", "EXTRA2"))
    HIDDEN3_EXTRA3 = "09", ParamEnumSettings(("HIDDEN3", "EXTRA3"))
    HIDDEN1 = EXTRA1 = HIDDEN1_EXTRA1[0]
    HIDDEN2 = EXTRA2 = HIDDEN2_EXTRA2[0]
    HIDDEN3 = EXTRA3 = HIDDEN3_EXTRA3[0]
    DVD_BD = "10", ParamEnumSettings(("DVD", "BD/DVD"))
    DVD = BD = DVD_BD[0]
    STRM_BOX = "11", ParamEnumSettings(zones=(Zone.MAIN, Zone.ZONE2, Zone.ZONE3))
    TV = "12", ParamEnumSettings(zones=(Zone.MAIN, Zone.ZONE2, Zone.ZONE3))
    TAPE = "20", ParamEnumSettings(("TAPE", "TV/TAPE"))
    TAPE2 = "21"
    PHONO = "22"
    CD = "23", ParamEnumSettings(("CD", "TV/CD"))
    FM = "24"
    AM = "25"
    TUNER = "26"
    MUSIC_SERVER_P4S_DLNA = "27", ParamEnumSettings(("MUSIC SERVER", "P4S", "DLNA"))
    MUSIC_SERVER = P4S = DLNA = MUSIC_SERVER_P4S_DLNA[0]
    INTERNET_RADIO = "28", ParamEnumSettings(extra_meanings="IRADIO FAVORITE")
    USB = "29", ParamEnumSettings(("USB", "USB (FRONT)"))
    USB_FRONT = USB[0]
    USB_REAR = "2A", ParamEnumSettings("USB (REAR)")
    NETWORK = "2B", ParamEnumSettings(extra_meanings="NET")
    # USB_TOGGLE = "2C", ParamEnumSettings("USB (TOGGLE)")
    AIRPLAY = "2D"
    BLUETOOTH = "2E"
    USB_DAC_IN = "2F", ParamEnumSettings(zones=(Zone.MAIN,))
    MULTI_CH = "30"
    XM = "31"
    SIRIUS = "32"
    DAB = "33"
    UNIVERSAL_PORT = "40"
    LINE = "41", ParamEnumSettings(zones=(Zone.MAIN,))
    LINE2 = "42", ParamEnumSettings(zones=(Zone.MAIN,))
    OPTICAL = "44", ParamEnumSettings(zones=(Zone.MAIN,))
    COAXIAL = "45", ParamEnumSettings(zones=(Zone.MAIN,))
    HDMI_5 = "55", ParamEnumSettings(zones=(Zone.MAIN, Zone.ZONE2))
    HDMI_6 = "56", ParamEnumSettings(zones=(Zone.MAIN, Zone.ZONE2))
    HDMI_7 = "57", ParamEnumSettings(zones=(Zone.MAIN, Zone.ZONE2))
    # OFF = "7F", ParamEnumSettings(zones=(Zone.ZONE2))
    MAIN_SOURCE = "80", ParamEnumSettings(zones=(Zone.ZONE2, Zone.ZONE3, Zone.ZONE4))


class ListeningModeParam(ParamEnum):
    P_00 = "00", ParamEnumSettings("STEREO", zones=(Zone.MAIN, Zone.ZONE2))
    P_01 = "01", ParamEnumSettings("DIRECT", zones=(Zone.MAIN, Zone.ZONE2))
    P_02 = "02", ParamEnumSettings("SURROUND", zones=(Zone.MAIN,))
    P_03 = "03", ParamEnumSettings(("FILM", "GAME RPG", "ADVANCED GAME"), zones=(Zone.MAIN,))
    P_04 = "04", ParamEnumSettings("THX", zones=(Zone.MAIN,))
    P_05 = "05", ParamEnumSettings(("ACTION", "GAME ACTION"), zones=(Zone.MAIN,))
    P_06 = "06", ParamEnumSettings(("MUSICAL", "GAME ROCK", "ROCK/POP"), zones=(Zone.MAIN,))
    P_07 = "07", ParamEnumSettings("MONO MOVIE", zones=(Zone.MAIN,))
    P_08 = "08", ParamEnumSettings(("ORCHESTRA", "CLASSICAL"), zones=(Zone.MAIN,))
    P_09 = "09", ParamEnumSettings("UNPLUGGED", zones=(Zone.MAIN,))
    P_0A = "0A", ParamEnumSettings(("STUDIO MIX", "ENTERTAINMENT SHOW"), zones=(Zone.MAIN,))
    P_0B = "0B", ParamEnumSettings(("TV LOGIC", "DRAMA"), zones=(Zone.MAIN,))
    P_0C = "0C", ParamEnumSettings(("ALL CH STEREO", "EXTENDED STEREO"), zones=(Zone.MAIN,))
    P_0D = (
        "0D",
        ParamEnumSettings(("THEATER DIMENSIONAL", "FRONT STAGE SURROUND"), zones=(Zone.MAIN,)),
    )
    P_0E = (
        "0E",
        ParamEnumSettings(("ENHANCED 7/ENHANCE", "GAME SPORTS", "SPORTS"), zones=(Zone.MAIN,)),
    )
    P_0F = "0F", ParamEnumSettings("MONO", zones=(Zone.MAIN, Zone.ZONE2))
    P_11 = "11", ParamEnumSettings(("PURE AUDIO", "PURE DIRECT"), zones=(Zone.MAIN,))
    P_12 = "12", ParamEnumSettings("MULTIPLEX", zones=(Zone.MAIN, Zone.ZONE2))
    P_13 = "13", ParamEnumSettings(("FULL MONO", "MONO MUSIC"), zones=(Zone.MAIN,))
    P_14 = "14", ParamEnumSettings("DOLBY VIRTUAL/SURROUND ENHANCER", zones=(Zone.MAIN,))
    P_15 = "15", ParamEnumSettings("DTS SURROUND SENSATION", zones=(Zone.MAIN,))
    P_16 = "16", ParamEnumSettings("AUDYSSEY DSX", zones=(Zone.MAIN,))
    P_17 = "17", ParamEnumSettings("DTS VIRTUAL:X", zones=(Zone.MAIN,))
    P_1F = "1F", ParamEnumSettings(("WHOLE HOUSE MODE", "MULTI ZONE MUSIC"), zones=(Zone.MAIN,))
    P_23 = "23", ParamEnumSettings("STAGE (JAPAN GENRE CONTROL)", zones=(Zone.MAIN,))
    P_25 = "25", ParamEnumSettings("ACTION (JAPAN GENRE CONTROL)", zones=(Zone.MAIN,))
    P_26 = "26", ParamEnumSettings("MUSIC (JAPAN GENRE CONTROL)", zones=(Zone.MAIN,))
    P_2E = "2E", ParamEnumSettings("SPORTS (JAPAN GENRE CONTROL)", zones=(Zone.MAIN,))
    P_40 = "40", ParamEnumSettings(("STRAIGHT DECODE", "5.1 CH SURROUND"), zones=(Zone.MAIN,))
    P_41 = "41", ParamEnumSettings("DOLBY EX/DTS ES", zones=(Zone.MAIN,))
    P_42 = "42", ParamEnumSettings("THX CINEMA", zones=(Zone.MAIN,))
    P_43 = "43", ParamEnumSettings("THX SURROUND EX", zones=(Zone.MAIN,))
    P_44 = "44", ParamEnumSettings("THX MUSIC", zones=(Zone.MAIN,))
    P_45 = "45", ParamEnumSettings("THX GAMES", zones=(Zone.MAIN,))
    P_50 = "50", ParamEnumSettings("THX U(2)/S(2)/I/S CINEMA", zones=(Zone.MAIN,))
    P_51 = "51", ParamEnumSettings("THX U(2)/S(2)/I/S MUSIC", zones=(Zone.MAIN,))
    P_52 = "52", ParamEnumSettings("THX U(2)/S(2)/I/S GAMES", zones=(Zone.MAIN,))
    P_80 = (
        "80",
        ParamEnumSettings(("DOLBY ATMOS/DOLBY SURROUND", "PLII/PLIIx MOVIE"), zones=(Zone.MAIN,)),
    )
    P_81 = "81", ParamEnumSettings("PLII/PLIIx MUSIC", zones=(Zone.MAIN,))
    P_82 = "82", ParamEnumSettings(("DTS:X/NEURAL:X", "NEO:6/NEO:X CINEMA"), zones=(Zone.MAIN,))
    P_83 = "83", ParamEnumSettings("NEO:6/NEO:X MUSIC", zones=(Zone.MAIN,))
    P_84 = (
        "84",
        ParamEnumSettings(
            ("DOLBY SURROUND THX CINEMA", "PLII/PLIIx THX CINEMA"), zones=(Zone.MAIN,)
        ),
    )
    P_85 = (
        "85",
        ParamEnumSettings(
            ("DTS NEURAL:X THX CINEMA", "NEO:6/NEO:X THX CINEMA"), zones=(Zone.MAIN,)
        ),
    )
    P_86 = "86", ParamEnumSettings("PLII/PLIIx GAME", zones=(Zone.MAIN,))
    P_87 = (
        "87",
        ParamEnumSettings("NEURAL SURR", extra_meanings="DVS (PI2)", zones=(Zone.MAIN, Zone.ZONE2)),
    )
    P_88 = (
        "88",
        ParamEnumSettings(
            "NEURAL THX/NEURAL SURROUND", extra_meanings="DVS (NEO6)", zones=(Zone.MAIN, Zone.ZONE2)
        ),
    )
    P_89 = (
        "89",
        ParamEnumSettings(("DOLBY SURROUND THX GAMES", "PLII/PLIIx THX GAMES"), zones=(Zone.MAIN,)),
    )
    P_8A = (
        "8A",
        ParamEnumSettings(("DTS NEURAL:X THX GAMES", "NEO:6/NEO:X THX GAMES"), zones=(Zone.MAIN,)),
    )
    P_8B = (
        "8B",
        ParamEnumSettings(("DOLBY SURROUND THX MUSIC", "PLII/PLIIx THX MUSIC"), zones=(Zone.MAIN,)),
    )
    P_8C = (
        "8C",
        ParamEnumSettings(("DTS NEURAL:X THX MUSIC", "NEO:6/NEO:X THX MUSIC"), zones=(Zone.MAIN,)),
    )
    P_8D = "8D", ParamEnumSettings("NEURAL THX CINEMA", zones=(Zone.MAIN,))
    P_8E = "8E", ParamEnumSettings("NEURAL THX MUSIC", zones=(Zone.MAIN,))
    P_8F = "8F", ParamEnumSettings("NEURAL THX GAMES", zones=(Zone.MAIN,))
    P_90 = "90", ParamEnumSettings("PLIIz HEIGHT", zones=(Zone.MAIN,))
    P_91 = "91", ParamEnumSettings("NEO:6 CINEMA DTS SURROUND SENSATION", zones=(Zone.MAIN,))
    P_92 = "92", ParamEnumSettings("NEO:6 MUSIC DTS SURROUND SENSATION", zones=(Zone.MAIN,))
    P_93 = "93", ParamEnumSettings("NEURAL DIGITAL MUSIC", zones=(Zone.MAIN,))
    P_94 = "94", ParamEnumSettings("PLIIz HEIGHT + THX CINEMA", zones=(Zone.MAIN,))
    P_95 = "95", ParamEnumSettings("PLIIz HEIGHT + THX MUSIC", zones=(Zone.MAIN,))
    P_96 = "96", ParamEnumSettings("PLIIz HEIGHT + THX GAMES", zones=(Zone.MAIN,))
    P_97 = "97", ParamEnumSettings("PLIIz HEIGHT + THX U2/S2 CINEMA", zones=(Zone.MAIN,))
    P_98 = "98", ParamEnumSettings("PLIIz HEIGHT + THX U2/S2 MUSIC", zones=(Zone.MAIN,))
    P_99 = "99", ParamEnumSettings("PLIIz HEIGHT + THX U2/S2 GAMES", zones=(Zone.MAIN,))
    P_9A = "9A", ParamEnumSettings("NEO:X GAME", zones=(Zone.MAIN,))
    P_A0 = "A0", ParamEnumSettings("PLIIx/PLII Movie + AUDYSSEY DSX", zones=(Zone.MAIN,))
    P_A1 = "A1", ParamEnumSettings("PLIIx/PLII MUSIC + AUDYSSEY DSX", zones=(Zone.MAIN,))
    P_A2 = "A2", ParamEnumSettings("PLIIx/PLII GAME + AUDYSSEY DSX", zones=(Zone.MAIN,))
    P_A3 = "A3", ParamEnumSettings("NEO:6 CINEMA + AUDYSSEY DSX", zones=(Zone.MAIN,))
    P_A4 = "A4", ParamEnumSettings("NEO:6 MUSIC + AUDYSSEY DSX", zones=(Zone.MAIN,))
    P_A5 = "A5", ParamEnumSettings("NEURAL SURROUND + AUDYSSEY DSX", zones=(Zone.MAIN,))
    P_A6 = "A6", ParamEnumSettings("NEURAL DIGITAL MUSIC + AUDYSSEY DSX", zones=(Zone.MAIN,))
    P_A7 = "A7", ParamEnumSettings("DOLBY EX + AUDYSSEY DSX", zones=(Zone.MAIN,))
    P_FF = "FF", ParamEnumSettings("AUTO SURROUND", zones=(Zone.MAIN,))
    # MOVIE = "MOVIE", ParamEnumSettings("MOVIE MODE WRAP-AROUND", zones=(Zone.MAIN,))
    # MUSIC = "MUSIC", ParamEnumSettings("MUSIC MODE WRAP-AROUND", zones=(Zone.MAIN,))
    # GAME = "GAME", ParamEnumSettings("GAME MODE WRAP-AROUND", zones=(Zone.MAIN,))
    # THX = "THX", ParamEnumSettings("THX MODE WRAP-AROUND", zones=(Zone.MAIN,))
    # AUTO = "AUTO", ParamEnumSettings("AUTO MODE WRAP-AROUND", zones=(Zone.MAIN,))
    # SURR = "SURR", ParamEnumSettings("SURR MODE WRAP-AROUND", zones=(Zone.MAIN,))
    # STEREO = "STEREO", ParamEnumSettings("STEREO MODE WRAP-AROUND", zones=(Zone.MAIN,))


class HDMIOutputParam(MainZoneParamEnum):
    NO_ANALOG = "00", ParamEnumSettings(("ANALOG", "NO"))
    NO = ANALOG = NO_ANALOG[0]
    MAIN_YES_HDMI = "01", ParamEnumSettings(("MAIN", "YES", "HDMI"))
    MAIN = YES = HDMI = MAIN_YES_HDMI[0]  # HDMI as opposed to ANALOG
    SUB_HDBASET = "02", ParamEnumSettings(("SUB", "HDBaseT"))
    SUB = HDBASET = SUB_HDBASET[0]
    BOTH = "03", ParamEnumSettings(extra_meanings="MAIN + SUB")
    BOTH_MAIN = "04", ParamEnumSettings("BOTH (MAIN)")
    BOTH_SUB = "05", ParamEnumSettings("BOTH (SUB)")


class TVOperationParam(MainZoneParamEnum):
    POWER = "POWER"
    PWRON = "PWRON", ParamEnumSettings("POWER ON")
    PWROFF = "PWROFF", ParamEnumSettings("POWER OFF")
    CHUP = "CHUP", ParamEnumSettings("CHANNEL UP")
    CHDN = "CHDN", ParamEnumSettings("CHANNEL DOWN")
    VLUP = "VLUP", ParamEnumSettings("VOLUME UP")
    VLDN = "VLDN", ParamEnumSettings("VOLUME DOWN")
    MUTE = "MUTE"
    DISP = "DISP", ParamEnumSettings("DISPLAY")
    INPUT = "INPUT"
    NUM_1 = "1", ParamEnumSettings("1")
    NUM_2 = "2", ParamEnumSettings("2")
    NUM_3 = "3", ParamEnumSettings("3")
    NUM_4 = "4", ParamEnumSettings("4")
    NUM_5 = "5", ParamEnumSettings("5")
    NUM_6 = "6", ParamEnumSettings("6")
    NUM_7 = "7", ParamEnumSettings("7")
    NUM_8 = "8", ParamEnumSettings("8")
    NUM_9 = "9", ParamEnumSettings("9")
    NUM_0 = "0", ParamEnumSettings("0")
    CLEAR = "CLEAR"
    SETUP = "SETUP"
    GUIDE = "GUIDE"
    PREV = "PREV", ParamEnumSettings("PREVIOUS")
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    ENTER = "ENTER"
    RETURN = "RETURN"
    A = "A"
    B = "B"
    C = "C"
    D = "D"


@dataclass
class ParamNumeric(_ParamBase):
    numeric_range: ClassVar[tuple[int, int]]

    numeric: int
    raw: bytes

    @classmethod
    def from_numeric(cls, numeric: int) -> Self:
        if not cls.numeric_range[0] <= numeric <= cls.numeric_range[1]:
            raise ValueError(f"Param outside of range: {numeric} in {cls.__name__}")
        sign = "+" if cls.numeric_range[0] < 0 and numeric != 0 else ""
        return cls(numeric, f"{numeric:{sign}02X}".encode())

    @classmethod
    def parse(cls, parameter: bytes) -> int:
        numeric = int(parameter, 16)
        if not cls.numeric_range[0] <= numeric <= cls.numeric_range[1]:
            raise ValueError(f"Param outside of range: {numeric} in {cls.__name__}")
        return numeric


class VolumeParamNumeric(ParamNumeric):
    numeric_range = (0, 200)


class ToneParam(ParamNumeric):
    numeric_range = (-10, 10)


class TunerPresetParam(ParamNumeric):
    numeric_range = (0, 40)


class DestinationArea(Enum):
    NORTH_AMERICA = "DX"
    EURASIA = "XX"
    JAPAN = "JJ"


__all__ = [
    "InputSourceParam",
    "ListeningModeParam",
    "HDMIOutputParam",
]
