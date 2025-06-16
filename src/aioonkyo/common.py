"""Common."""

from dataclasses import dataclass


class OnkyoError(Exception):
    """Onkyo Error."""


@dataclass(kw_only=True)
class BasicReceiverInfo:
    """Basic receiver information."""

    host: str
    port: int = 60128


@dataclass(kw_only=True)
class ReceiverInfo(BasicReceiverInfo):
    """Receiver information."""

    ip: str
    model_name: str
    identifier: str


__all__ = [
    "BasicReceiverInfo",
    "ReceiverInfo",
]
