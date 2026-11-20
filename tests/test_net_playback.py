"""NET/USB messages decoded from and encoded into complete eISCP frames."""

# Keep the suite runnable with the standard library.
# ruff: noqa: PT009, PT027

import struct
import unittest

from aioonkyo import (
    Code,
    Kind,
    NetArtPacket,
    NetArtType,
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
        for code, kind in (
            (b"NST", Kind.NET_PLAY_STATUS),
            (b"NTC", Kind.NET_OPERATION),
            (b"NMS", Kind.NET_MENU),
            (b"NTS", Kind.NET_TIME_SEEK),
            (b"NJA", Kind.NET_JACKET_ART),
        ):
            message = _read(code + b"N/A")
            self.assertIsInstance(message, status.NotAvailable)
            self.assertEqual(message.kind, kind)

        for code, parameter in ((b"NTC", b"PLAY"), (b"NTC", b"CUSTOM"), (b"NTS", b"00:01:00")):
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
            (b"NMS", query.NetMenu()),
            (b"NJA", query.NetJacketArt()),
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

    def test_menu(self) -> None:
        """Read the Time Seek flag and service id out of the menu status."""
        for parameter, track_menu, seek, service in (
            (b"m0000S100", True, True, "00"),
            (b"xxxxxx10a", False, False, "0A"),
            (b"mxxxx?x1E", True, None, "1E"),
            (b"xxxxxx1xx", False, False, None),
            (b"m0000S1zz", True, True, None),
            (b"xxxxxS", False, True, None),
            (b"", None, None, None),
        ):
            with self.subTest(parameter=parameter):
                message = _read(b"NMS" + parameter)
                self.assertIsInstance(message, status.NetMenu)
                self.assertEqual(
                    (message.track_menu, message.seek, message.service), (track_menu, seek, service)
                )

    def test_jacket_art(self) -> None:
        """Expose art URLs, image packets, missing art and unrecognized reports."""
        url = b"http://192.0.2.10/album_art.cgi"
        for parameter, image_type, packet, data, expected_url in (
            (b"2-" + url, NetArtType.URL, NetArtPacket.SINGLE, url, url.decode()),
            (b"2-", NetArtType.URL, NetArtPacket.SINGLE, b"", None),
            (b"2-N/A", NetArtType.URL, NetArtPacket.SINGLE, b"N/A", None),
            (b"n-", NetArtType.NONE, NetArtPacket.SINGLE, b"", None),
            (b"10FFD8", NetArtType.JPEG, NetArtPacket.START, b"FFD8", None),
            (b"0242", NetArtType.BMP, NetArtPacket.END, b"42", None),
            (b"20" + url, NetArtType.URL, NetArtPacket.START, url, None),
            (b"LINK\x1a\n\n", None, None, b"LINK", None),
        ):
            with self.subTest(parameter=parameter):
                message = _read(b"NJA" + parameter)
                self.assertIsInstance(message, status.NetJacketArt)
                self.assertEqual(
                    (message.image_type, message.packet, message.data), (image_type, packet, data)
                )
                self.assertEqual(message.url, expected_url)

    def test_jacket_art_commands(self) -> None:
        """Set the art mode, or ask for the current art itself."""
        key = command.NetJacketArt.Param
        for param, payload in (
            (key.ENABLE, b"ENA"),
            (key.DISABLE, b"DIS"),
            (key.BMP, b"BMP"),
            (key.LINK, b"LINK"),
            (key.UP, b"UP"),
            (key.REQUEST, b"REQ"),
        ):
            with self.subTest(param=param):
                frame = EISCPPacket.from_instruction_message(command.NetJacketArt(param))
                self.assertEqual(frame.raw, _packet(b"!1NJA" + payload + b"\r\n"))

    def test_time_seek(self) -> None:
        """Seek with an hh:mm:ss position and reject positions NTS cannot express."""
        for position, payload in ((0, b"00:00:00"), (3723, b"01:02:03"), (359999, b"99:59:59")):
            with self.subTest(position=position):
                frame = EISCPPacket.from_instruction_message(command.NetTimeSeek(position))
                self.assertEqual(frame.raw, _packet(b"!1NTS" + payload + b"\r\n"))
        for position in (-1, 360000):
            with self.subTest(position=position), self.assertRaises(ValueError):
                command.NetTimeSeek(position)
