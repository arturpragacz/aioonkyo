"""Messages."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TypedDict, Unpack

from .message_code import Code, Kind, Zone
from .parameter import ParamEnum


class KnownMessage:
    """Abstract known message.

    Each subclass needs to provide `parameter`.
    Each subclass needs to provide `code` or (`kind` and `zone`).
    """

    parameter: bytes

    @cached_property
    def code(self) -> Code:
        return Code.from_kind_zone(self.kind, self.zone)

    @cached_property
    def zone(self) -> Zone:
        return self.code.zone

    @cached_property
    def kind(self) -> Kind:
        return self.code.kind

    @cached_property
    def raw(self) -> bytes:
        return self.code.raw + self.parameter

    def _validate(self, **kwargs: Unpack[ValidateKwargs]) -> None:
        pass


class ValidateKwargs(TypedDict, total=False):
    param: ParamEnum


@dataclass
class RawMessage:
    raw_code: bytes
    parameter: bytes

    @cached_property
    def raw(self) -> bytes:
        return self.raw_code + self.parameter


type Message = KnownMessage | RawMessage


class CheckParamZonesMixin(KnownMessage):
    def _validate(self, **kwargs: Unpack[ValidateKwargs]) -> None:
        param = kwargs.get("param")
        if param is None:
            raise ValueError(f"No param to check zone {self.zone}: {self}")
        if param.zones and self.zone not in param.zones:
            raise ValueError(f"Invalid zone {self.zone} for param {param}: {self}")
        super()._validate(**kwargs)


# __all__ = [
#     "KnownMessage",
#     "RawMessage",
#     "Message",
# ]
