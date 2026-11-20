"""NET/USB messages decoded from and encoded into complete eISCP frames."""

# Keep the suite runnable with the standard library.
# ruff: noqa: PT009

import struct
import unittest

from aioonkyo import (
    Code,
    Kind,
    NetPlaybackState,
    NetRepeatMode,
    NetShuffleMode,
    Status,
    Zone,
    command,
    query,
    status,
)
from aioonkyo.protocol import EISCPPacket


def _packet(payload: bytes) -> bytes:
    return struct.pack("!4sIIB3x", b"ISCP", 16, len(payload), 1) + payload


def _read(message: bytes) -> Status:
    return EISCPPacket.parse_status(_packet(b"!1" + message + b"\x1a\r\n")).iscp.message


class TestNetPlayback(unittest.TestCase):
    """Exercise the public message types through the wire codec."""

    def test_playback(self) -> None:
        """Playback, repeat and shuffle retain their separate wire meanings."""
        for payload, playback, repeat, shuffle in (
            (b"S--", NetPlaybackState.STOPPED, NetRepeatMode.OFF, NetShuffleMode.OFF),
            (b"PRS", NetPlaybackState.PLAYING, NetRepeatMode.ALL, NetShuffleMode.ALL),
            (b"p1A", NetPlaybackState.PAUSED, NetRepeatMode.ONE, NetShuffleMode.ALBUM),
            (b"FFF", NetPlaybackState.FAST_FORWARD, NetRepeatMode.FOLDER, NetShuffleMode.FOLDER),
            (b"R", NetPlaybackState.FAST_REVERSE, None, None),
            (b"E?S", NetPlaybackState.END, None, NetShuffleMode.ALL),
            (b"Q-S", None, NetRepeatMode.OFF, NetShuffleMode.ALL),
            (b"Pxx1", NetPlaybackState.PLAYING, NetRepeatMode.DISABLED, NetShuffleMode.DISABLED),
        ):
            with self.subTest(payload=payload):
                message = _read(b"NST" + payload)
                self.assertIsInstance(message, status.NetPlayStatus)
                self.assertEqual(
                    (message.playback, message.repeat, message.shuffle), (playback, repeat, shuffle)
                )
                self.assertEqual(message.code, Code.NST)
                self.assertEqual(message.zone, Zone.MAIN)
                self.assertEqual(message.parameter, payload)

    def test_text(self) -> None:
        """Keep empty metadata, UTF-8, display whitespace and original payloads."""
        for code, cls in (
            (b"NTI", status.NetTitle),
            (b"NAT", status.NetArtist),
            (b"NAL", status.NetAlbum),
        ):
            for parameter, expected in (
                (b"", ""),
                (" Björk ".encode(), " Björk "),
                (b"title\xff\x1a\n\n", "title\ufffd"),
            ):
                with self.subTest(code=code, parameter=parameter):
                    message = _read(code + parameter)
                    self.assertIsInstance(message, cls)
                    self.assertEqual(message.text, expected)
                    self.assertEqual(message.parameter, parameter)

    def test_time(self) -> None:
        """Read clocks independently, including live streams and buffering."""
        for parameter, position, duration in (
            (b"00:02:01/01:02:03", 121, 3723),
            (b"00:00/--:--", 0, None),
            (b"--:--:--/03:00", None, 180),
            (b"02:10", 130, None),
            (b"99:59/99:59:59", 5999, 359999),
            (b"100:00/100:00:00", None, None),
            (b"00:60:01/02:60", None, None),
            (b"+1:20/10:00", None, 600),
        ):
            with self.subTest(parameter=parameter):
                message = _read(b"NTM" + parameter)
                self.assertIsInstance(message, status.NetTime)
                self.assertEqual((message.position, message.duration), (position, duration))

    def test_track(self) -> None:
        """Read current and total track numbers, preserving partial reports."""
        for parameter, current, total in (
            (b"0002/0012", 2, 12),
            (b"0002/----", 2, None),
            (b"----/----", None, None),
            (b"0002", 2, None),
        ):
            with self.subTest(parameter=parameter):
                message = _read(b"NTR" + parameter)
                self.assertIsInstance(message, status.NetTrack)
                self.assertEqual((message.current, message.total), (current, total))

    def test_other_responses(self) -> None:
        """Keep unavailable, echo and unimplemented messages accessible."""
        for code, kind in ((b"NST", Kind.NET_PLAY_STATUS), (b"NTC", Kind.NET_OPERATION)):
            message = _read(code + b"N/A")
            self.assertIsInstance(message, status.NotAvailable)
            self.assertEqual(message.kind, kind)

        for code, parameter in ((b"NTC", b"PLAY"), (b"NTC", b"CUSTOM"), (b"NJA", b"n-")):
            self.assertEqual(_read(code + parameter), status.Raw(code, parameter))

    def test_queries(self) -> None:
        """Query each supported status on the network player."""
        for code, instruction in (
            (b"NST", query.NetPlayStatus()),
            (b"NTI", query.NetTitle()),
            (b"NAT", query.NetArtist()),
            (b"NAL", query.NetAlbum()),
            (b"NTM", query.NetTime()),
            (b"NTR", query.NetTrack()),
        ):
            with self.subTest(code=code):
                frame = EISCPPacket.from_instruction_message(instruction)
                self.assertEqual(frame.raw, _packet(b"!1" + code + b"QSTN\r\n"))

    def test_keys(self) -> None:
        """Each remote-control key sends a single key press."""
        key = command.NetOperation.Param
        for param, payload in (
            (key.PLAY, b"PLAY"),
            (key.PAUSE, b"PAUSE"),
            (key.STOP, b"STOP"),
            (key.NEXT, b"TRUP"),
            (key.PREVIOUS, b"TRDN"),
            (key.REPEAT, b"REPEAT"),
            (key.RANDOM, b"RANDOM"),
            (key.PLAY_PAUSE, b"P/P"),
            (key.FAST_FORWARD, b"FF"),
            (key.REWIND, b"REW"),
            (key.REPEAT_SHUFFLE, b"REP/SHF"),
            (key.NUM_0, b"0"),
            (key.CHUP, b"CHUP"),
            (key.F2, b"F2"),
        ):
            with self.subTest(param=param):
                frame = EISCPPacket.from_instruction_message(command.NetOperation(param))
                self.assertEqual(frame.raw, _packet(b"!1NTC" + payload + b"\r\n"))
