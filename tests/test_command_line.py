import functools
import os
import re
import sys
import tempfile
import types
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import cantools
import cantools.database


def with_fake_screen_width(screen_width):
    def decorator(test_method):
        @functools.wraps(test_method)
        def wrapper(*args, **kwargs):
            default_curses = None
            try:
                import curses
            except ImportError:
                pass
            else:
                default_curses = curses
                curses_mock_name = 'curses_mock'
                curses_mock = types.ModuleType(curses_mock_name)
                sys.modules['curses'] = curses_mock
                curses_mock.initscr = lambda: types.SimpleNamespace(getmaxyx=lambda: (0, screen_width))
                curses_mock.endwin = lambda: None

            test_method_return = test_method(*args, **kwargs)

            if default_curses is not None:
                sys.modules['curses'] = default_curses

            # A test method doesn't return anything, but return anyway to be
            # completely transparent.
            return test_method_return
        return wrapper
    return decorator


def remove_date_time(string):
    return re.sub(r'.*This.* file was generated.*', '', string)


def read_file(filename):
    with open(filename) as fin:
        return remove_date_time(fin.read())


def read_utf8_file(filename):
    """Reference files are encoded with UTF-8.

    """

    with open(filename, encoding='utf-8') as fin:
        return remove_date_time(fin.read())


class CanToolsCommandLineTest(unittest.TestCase):
    maxDiff = None

    def assert_files_equal(self, actual, expected):
        # open(expected, 'w').write(read_utf8_file(actual))
        self.assertEqual(read_file(actual), read_utf8_file(expected))

    def test_decode(self):
        argv = ['cantools', 'decode', 'tests/files/dbc/socialledge.dbc']
        input_data = """\
  vcan0  0C8   [8]  F0 00 00 00 00 00 00 00
  vcan0  064   [10]  F0 01 FF FF FF FF FF FF FF FF
  vcan0  ERROR

  vcan0  1F4   [4]  01 02 03 04
  vcan0  1F3   [3]  01 02 03
"""

        expected_output = """\
  vcan0  0C8   [8]  F0 00 00 00 00 00 00 00 ::
SENSOR_SONARS(
    SENSOR_SONARS_mux: 0,
    SENSOR_SONARS_err_count: 15,
    SENSOR_SONARS_left: 0.0,
    SENSOR_SONARS_middle: 0.0,
    SENSOR_SONARS_right: 0.0,
    SENSOR_SONARS_rear: 0.0
)
  vcan0  064   [10]  F0 01 FF FF FF FF FF FF FF FF :: Wrong data size: 10 instead of 1 bytes
  vcan0  ERROR

  vcan0  1F4   [4]  01 02 03 04 ::
IO_DEBUG(
    IO_DEBUG_test_unsigned: 1,
    IO_DEBUG_test_enum: IO_DEBUG_test2_enum_two,
    IO_DEBUG_test_signed: 3,
    IO_DEBUG_test_float: 2.0
)
  vcan0  1F3   [3]  01 02 03 :: Unknown frame id 499 (0x1f3)
"""

        stdout = StringIO()

        with patch('sys.stdin', StringIO(input_data)):
            with patch('sys.stdout', stdout):
                with patch('sys.argv', argv):
                    cantools._main()
                    actual_output = stdout.getvalue()
                    self.assertEqual(actual_output, expected_output)

    def test_decode_timestamp_absolute(self):
        argv = [
            'cantools',
            'decode',
            '--prune',
            'tests/files/dbc/socialledge.dbc'
        ]
        input_data = """\
 (2020-12-19 12:04:45.485261)  vcan0  0C8   [8]  F0 00 00 00 00 00 00 00
 (2020-12-19 12:04:48.597222)  vcan0  064   [8]  F0 01 FF FF FF FF FF FF
 (2020-12-19 12:04:56.805087)  vcan0  1F4   [4]  01 02 03 04
 (2020-12-19 12:04:59.085517)  vcan0  1F3   [3]  01 02 03
"""

        expected_output = """\
 (2020-12-19 12:04:45.485261)  vcan0  0C8   [8]  F0 00 00 00 00 00 00 00 ::
SENSOR_SONARS(
    SENSOR_SONARS_mux: 0,
    SENSOR_SONARS_err_count: 15,
    SENSOR_SONARS_left: 0.0,
    SENSOR_SONARS_middle: 0.0,
    SENSOR_SONARS_right: 0.0,
    SENSOR_SONARS_rear: 0.0
)
 (2020-12-19 12:04:48.597222)  vcan0  064   [8]  F0 01 FF FF FF FF FF FF :: Wrong data size: 8 instead of 1 bytes
 (2020-12-19 12:04:56.805087)  vcan0  1F4   [4]  01 02 03 04 ::
IO_DEBUG(
    IO_DEBUG_test_unsigned: 1,
    IO_DEBUG_test_enum: two,
    IO_DEBUG_test_signed: 3,
    IO_DEBUG_test_float: 2.0
)
 (2020-12-19 12:04:59.085517)  vcan0  1F3   [3]  01 02 03 :: Unknown frame id 499 (0x1f3)
"""

        stdout = StringIO()

        with patch('sys.stdin', StringIO(input_data)):
            with patch('sys.stdout', stdout):
                with patch('sys.argv', argv):
                    cantools._main()
                    actual_output = stdout.getvalue()
                    self.assertEqual(actual_output, expected_output)

    def test_decode_timestamp_zero(self):
        argv = [
            'cantools',
            'decode',
            '--prune',
            'tests/files/dbc/socialledge.dbc'
        ]
        input_data = """\
 (000.000000)  vcan0  0C8   [8]  F0 00 00 00 00 00 00 00
 (002.047817)  vcan0  064   [8]  F0 01 FF FF FF FF FF FF
 (012.831664)  vcan0  1F4   [4]  01 02 03 04
 (015.679614)  vcan0  1F3   [3]  01 02 03
"""

        expected_output = """\
 (000.000000)  vcan0  0C8   [8]  F0 00 00 00 00 00 00 00 ::
SENSOR_SONARS(
    SENSOR_SONARS_mux: 0,
    SENSOR_SONARS_err_count: 15,
    SENSOR_SONARS_left: 0.0,
    SENSOR_SONARS_middle: 0.0,
    SENSOR_SONARS_right: 0.0,
    SENSOR_SONARS_rear: 0.0
)
 (002.047817)  vcan0  064   [8]  F0 01 FF FF FF FF FF FF :: Wrong data size: 8 instead of 1 bytes
 (012.831664)  vcan0  1F4   [4]  01 02 03 04 ::
IO_DEBUG(
    IO_DEBUG_test_unsigned: 1,
    IO_DEBUG_test_enum: two,
    IO_DEBUG_test_signed: 3,
    IO_DEBUG_test_float: 2.0
)
 (015.679614)  vcan0  1F3   [3]  01 02 03 :: Unknown frame id 499 (0x1f3)
"""

        stdout = StringIO()

        with patch('sys.stdin', StringIO(input_data)):
            with patch('sys.stdout', stdout):
                with patch('sys.argv', argv):
                    cantools._main()
                    actual_output = stdout.getvalue()
                    self.assertEqual(actual_output, expected_output)

    def test_decode_can_fd(self):
        argv = ['cantools', 'decode', 'tests/files/dbc/foobar.dbc']
        input_data = """\
  vcan0  12333 [064]  02 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
"""

        expected_output = """\
  vcan0  12333 [064]  02 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ::
CanFd(
    Fie: 2,
    Fas: 1
)
"""

        stdout = StringIO()

        with patch('sys.stdin', StringIO(input_data)):
            with patch('sys.stdout', stdout):
                with patch('sys.argv', argv):
                    cantools._main()
                    actual_output = stdout.getvalue()
                    self.assertEqual(actual_output, expected_output)

    def test_decode_log_format(self):
        argv = [
            'cantools',
            'decode',
            '--prune',
            'tests/files/dbc/socialledge.dbc'
        ]
        input_data = """\
(1594172461.968006) vcan0 0C8#F000000000000000
(1594172462.968006) vcan0 0C8#F000000000000000 T
(1594172463.968006) vcan0 0C8#F000000000000000 R
(1594172462.126542) vcan0 064#F001FFFFFFFFFFFFFFFF
(1594172462.127684) vcan0 ERROR

(1594172462.356874) vcan0 1F4#01020304
(1594172462.688432) vcan0 1F3#010203
"""

        expected_output = """\
(1594172461.968006) vcan0 0C8#F000000000000000 ::
SENSOR_SONARS(
    SENSOR_SONARS_mux: 0,
    SENSOR_SONARS_err_count: 15,
    SENSOR_SONARS_left: 0.0,
    SENSOR_SONARS_middle: 0.0,
    SENSOR_SONARS_right: 0.0,
    SENSOR_SONARS_rear: 0.0
)
(1594172462.968006) vcan0 0C8#F000000000000000 T ::
SENSOR_SONARS(
    SENSOR_SONARS_mux: 0,
    SENSOR_SONARS_err_count: 15,
    SENSOR_SONARS_left: 0.0,
    SENSOR_SONARS_middle: 0.0,
    SENSOR_SONARS_right: 0.0,
    SENSOR_SONARS_rear: 0.0
)
(1594172463.968006) vcan0 0C8#F000000000000000 R ::
SENSOR_SONARS(
    SENSOR_SONARS_mux: 0,
    SENSOR_SONARS_err_count: 15,
    SENSOR_SONARS_left: 0.0,
    SENSOR_SONARS_middle: 0.0,
    SENSOR_SONARS_right: 0.0,
    SENSOR_SONARS_rear: 0.0
)
(1594172462.126542) vcan0 064#F001FFFFFFFFFFFFFFFF :: Wrong data size: 10 instead of 1 bytes
(1594172462.127684) vcan0 ERROR

(1594172462.356874) vcan0 1F4#01020304 ::
IO_DEBUG(
    IO_DEBUG_test_unsigned: 1,
    IO_DEBUG_test_enum: two,
    IO_DEBUG_test_signed: 3,
    IO_DEBUG_test_float: 2.0
)
(1594172462.688432) vcan0 1F3#010203 :: Unknown frame id 499 (0x1f3)
"""

        stdout = StringIO()

        with patch('sys.stdin', StringIO(input_data)):
            with patch('sys.stdout', stdout):
                with patch('sys.argv', argv):
                    cantools._main()
                    actual_output = stdout.getvalue()
                    self.assertEqual(actual_output, expected_output)

    def test_single_line_decode(self):
        argv = [
            'cantools',
            'decode',
            '--prune',
            '--single-line',
            'tests/files/dbc/socialledge.dbc'
        ]

        input_data = """\
  vcan0  0C8   [8]  F0 00 00 00 00 00 00 00
  vcan0  064   [10]  F0 01 FF FF FF FF FF FF FF FF
  vcan0  ERROR

  vcan0  1F4   [4]  01 02 03 04
  vcan0  1F3   [3]  01 02 03
"""

        expected_output = """\
  vcan0  0C8   [8]  F0 00 00 00 00 00 00 00 :: SENSOR_SONARS(SENSOR_SONARS_mux: 0, SENSOR_SONARS_err_count: 15, SENSOR_SONARS_left: 0.0, SENSOR_SONARS_middle: 0.0, SENSOR_SONARS_right: 0.0, SENSOR_SONARS_rear: 0.0)
  vcan0  064   [10]  F0 01 FF FF FF FF FF FF FF FF :: Wrong data size: 10 instead of 1 bytes
  vcan0  ERROR

  vcan0  1F4   [4]  01 02 03 04 :: IO_DEBUG(IO_DEBUG_test_unsigned: 1, IO_DEBUG_test_enum: two, IO_DEBUG_test_signed: 3, IO_DEBUG_test_float: 2.0)
  vcan0  1F3   [3]  01 02 03 :: Unknown frame id 499 (0x1f3)
"""

        stdout = StringIO()

        with patch('sys.stdin', StringIO(input_data)):
            with patch('sys.stdout', stdout):
                with patch('sys.argv', argv):
                    cantools._main()
                    actual_output = stdout.getvalue()
                    self.assertEqual(actual_output, expected_output)

    def test_single_line_decode_log_format(self):
        argv = [
            'cantools',
            'decode',
            '--prune',
            '--single-line',
            'tests/files/dbc/socialledge.dbc'
        ]

        input_data = """\
(1594172461.968006) vcan0 0C8#F000000000000000
(1594172462.126542) vcan0 064#F001FFFFFFFFFFFFFFFF
(1594172462.127684) vcan0 ERROR

(1594172462.356874) vcan0 1F4#01020304
(1594172462.688432) vcan0 1F3#010203
"""

        expected_output = """\
(1594172461.968006) vcan0 0C8#F000000000000000 :: SENSOR_SONARS(SENSOR_SONARS_mux: 0, SENSOR_SONARS_err_count: 15, SENSOR_SONARS_left: 0.0, SENSOR_SONARS_middle: 0.0, SENSOR_SONARS_right: 0.0, SENSOR_SONARS_rear: 0.0)
(1594172462.126542) vcan0 064#F001FFFFFFFFFFFFFFFF :: Wrong data size: 10 instead of 1 bytes
(1594172462.127684) vcan0 ERROR

(1594172462.356874) vcan0 1F4#01020304 :: IO_DEBUG(IO_DEBUG_test_unsigned: 1, IO_DEBUG_test_enum: two, IO_DEBUG_test_signed: 3, IO_DEBUG_test_float: 2.0)
(1594172462.688432) vcan0 1F3#010203 :: Unknown frame id 499 (0x1f3)
"""

        stdout = StringIO()

        with patch('sys.stdin', StringIO(input_data)):
            with patch('sys.stdout', stdout):
                with patch('sys.argv', argv):
                    cantools._main()
                    actual_output = stdout.getvalue()
                    self.assertEqual(actual_output, expected_output)

    def test_decode_muxed_data(self):
        argv = [
            'cantools',
            'decode',
            'tests/files/dbc/msxii_system_can.dbc'
        ]

        input_data = """\
  vcan0  401   [6]  00 00 98 98 0B 00
  vcan0  401   [6]  01 00 9C 98 0A 00
  vcan0  401   [6]  02 00 B5 98 0A 00
  vcan0  401   [6]  03 00 9D 98 0A 00
  vcan0  401   [6]  04 00 CB 98 0B 00
  vcan0  401   [6]  05 00 C5 98 0B 00
  vcan0  401   [6]  06 00 35 9A EA 59
  vcan0  401   [6]  07 00 B1 98 FA 59
  vcan0  401   [6]  08 00 A5 98 0B 00
  vcan0  401   [6]  09 00 73 99 0C 00
  vcan0  401   [6]  0A 00 66 98 0B 00
  vcan0  401   [6]  0B 00 65 96 0B 00
  vcan0  401   [6]  0C 00 72 99 B3 5A
  vcan0  401   [6]  0D 00 04 99 9D 5A
  vcan0  401   [6]  0E 00 F8 9A C4 5A
  vcan0  401   [6]  0F 00 3B 9C 89 5A
  vcan0  401   [6]  10 00 8E 9A DE 5A
  vcan0  401   [6]  11 00 E8 9B DE 5A
  vcan0  401   [6]  12 00 D5 99 C9 59
  vcan0  401   [6]  13 00 EE 99 0D 5A
  vcan0  401   [6]  14 00 83 99 02 5A
  vcan0  401   [6]  15 00 97 99 12 5A
  vcan0  401   [6]  16 00 F6 99 0C 5A
  vcan0  401   [6]  17 00 0E 9B C4 59
  vcan0  401   [6]  18 00 68 9A 42 5A
  vcan0  401   [6]  19 00 83 99 22 5A
  vcan0  401   [6]  1A 00 85 99 3D 5A
  vcan0  401   [6]  1B 00 EF 99 2F 5A
  vcan0  401   [6]  1C 00 7E 99 50 5A
  vcan0  401   [6]  1D 00 39 9A 21 5A
  vcan0  401   [6]  1E 00 44 99 F9 59
  vcan0  401   [6]  1F 00 60 99 1B 5A
  vcan0  401   [6]  20 00 42 99 0A 5A
  vcan0  401   [6]  21 00 C3 9A 33 5A
  vcan0  401   [6]  22 00 3D 99 1A 5A
  vcan0  401   [6]  23 00 59 99 5C 5A
"""

        expected_output = """\
  vcan0  401   [6]  00 00 98 98 0B 00 ::
BATTERY_VT(
    BATTERY_VT_INDEX: 0,
    MODULE_VOLTAGE_00: 39064,
    MODULE_TEMP_00: 11
)
  vcan0  401   [6]  01 00 9C 98 0A 00 ::
BATTERY_VT(
    BATTERY_VT_INDEX: 1,
    MODULE_VOLTAGE_01: 39068,
    MODULE_TEMP_01: 10
)
  vcan0  401   [6]  02 00 B5 98 0A 00 ::
BATTERY_VT(
    BATTERY_VT_INDEX: 2,
    MODULE_VOLTAGE_02: 39093,
    MODULE_TEMP_02: 10
)
  vcan0  401   [6]  03 00 9D 98 0A 00 ::
BATTERY_VT(
    BATTERY_VT_INDEX: 3,
    MODULE_VOLTAGE_03: 39069,
    MODULE_TEMP_03: 10
)
  vcan0  401   [6]  04 00 CB 98 0B 00 ::
BATTERY_VT(
    BATTERY_VT_INDEX: 4,
    MODULE_VOLTAGE_04: 39115,
    MODULE_TEMP_04: 11
)
  vcan0  401   [6]  05 00 C5 98 0B 00 ::
BATTERY_VT(
    BATTERY_VT_INDEX: 5,
    MODULE_VOLTAGE_05: 39109,
    MODULE_TEMP_05: 11
)
  vcan0  401   [6]  06 00 35 9A EA 59 ::
BATTERY_VT(
    BATTERY_VT_INDEX: 6,
    MODULE_VOLTAGE_06: 39477,
    MODULE_TEMP_06: 23018
)
  vcan0  401   [6]  07 00 B1 98 FA 59 ::
BATTERY_VT(
    BATTERY_VT_INDEX: 7,
    MODULE_VOLTAGE_07: 39089,
    MODULE_TEMP_07: 23034
)
  vcan0  401   [6]  08 00 A5 98 0B 00 ::
BATTERY_VT(
    BATTERY_VT_INDEX: 8,
    MODULE_VOLTAGE_08: 39077,
    MODULE_TEMP_08: 11
)
  vcan0  401   [6]  09 00 73 99 0C 00 ::
BATTERY_VT(
    BATTERY_VT_INDEX: 9,
    MODULE_VOLTAGE_09: 39283,
    MODULE_TEMP_09: 12
)
  vcan0  401   [6]  0A 00 66 98 0B 00 ::
BATTERY_VT(
    BATTERY_VT_INDEX: 10,
    MODULE_VOLTAGE_10: 39014,
    MODULE_TEMP_10: 11
)
  vcan0  401   [6]  0B 00 65 96 0B 00 ::
BATTERY_VT(
    BATTERY_VT_INDEX: 11,
    MODULE_VOLTAGE_11: 38501,
    MODULE_TEMP_11: 11
)
  vcan0  401   [6]  0C 00 72 99 B3 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 12,
    MODULE_VOLTAGE_12: 39282,
    MODULE_TEMP_12: 23219
)
  vcan0  401   [6]  0D 00 04 99 9D 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 13,
    MODULE_VOLTAGE_13: 39172,
    MODULE_TEMP_13: 23197
)
  vcan0  401   [6]  0E 00 F8 9A C4 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 14,
    MODULE_VOLTAGE_14: 39672,
    MODULE_TEMP_14: 23236
)
  vcan0  401   [6]  0F 00 3B 9C 89 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 15,
    MODULE_VOLTAGE_15: 39995,
    MODULE_TEMP_15: 23177
)
  vcan0  401   [6]  10 00 8E 9A DE 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 16,
    MODULE_VOLTAGE_16: 39566,
    MODULE_TEMP_16: 23262
)
  vcan0  401   [6]  11 00 E8 9B DE 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 17,
    MODULE_VOLTAGE_17: 39912,
    MODULE_TEMP_17: 23262
)
  vcan0  401   [6]  12 00 D5 99 C9 59 ::
BATTERY_VT(
    BATTERY_VT_INDEX: 18,
    MODULE_VOLTAGE_18: 39381,
    MODULE_TEMP_18: 22985
)
  vcan0  401   [6]  13 00 EE 99 0D 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 19,
    MODULE_VOLTAGE_19: 39406,
    MODULE_TEMP_19: 23053
)
  vcan0  401   [6]  14 00 83 99 02 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 20,
    MODULE_VOLTAGE_20: 39299,
    MODULE_TEMP_20: 23042
)
  vcan0  401   [6]  15 00 97 99 12 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 21,
    MODULE_VOLTAGE_21: 39319,
    MODULE_TEMP_21: 23058
)
  vcan0  401   [6]  16 00 F6 99 0C 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 22,
    MODULE_VOLTAGE_22: 39414,
    MODULE_TEMP_22: 23052
)
  vcan0  401   [6]  17 00 0E 9B C4 59 ::
BATTERY_VT(
    BATTERY_VT_INDEX: 23,
    MODULE_VOLTAGE_23: 39694,
    MODULE_TEMP_23: 22980
)
  vcan0  401   [6]  18 00 68 9A 42 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 24,
    MODULE_VOLTAGE_24: 39528,
    MODULE_TEMP_24: 23106
)
  vcan0  401   [6]  19 00 83 99 22 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 25,
    MODULE_VOLTAGE_25: 39299,
    MODULE_TEMP_25: 23074
)
  vcan0  401   [6]  1A 00 85 99 3D 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 26,
    MODULE_VOLTAGE_26: 39301,
    MODULE_TEMP_26: 23101
)
  vcan0  401   [6]  1B 00 EF 99 2F 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 27,
    MODULE_VOLTAGE_27: 39407,
    MODULE_TEMP_27: 23087
)
  vcan0  401   [6]  1C 00 7E 99 50 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 28,
    MODULE_VOLTAGE_28: 39294,
    MODULE_TEMP_28: 23120
)
  vcan0  401   [6]  1D 00 39 9A 21 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 29,
    MODULE_VOLTAGE_29: 39481,
    MODULE_TEMP_29: 23073
)
  vcan0  401   [6]  1E 00 44 99 F9 59 ::
BATTERY_VT(
    BATTERY_VT_INDEX: 30,
    MODULE_VOLTAGE_30: 39236,
    MODULE_TEMP_30: 23033
)
  vcan0  401   [6]  1F 00 60 99 1B 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 31,
    MODULE_VOLTAGE_31: 39264,
    MODULE_TEMP_31: 23067
)
  vcan0  401   [6]  20 00 42 99 0A 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 32,
    MODULE_VOLTAGE_32: 39234,
    MODULE_TEMP_32: 23050
)
  vcan0  401   [6]  21 00 C3 9A 33 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 33,
    MODULE_VOLTAGE_33: 39619,
    MODULE_TEMP_33: 23091
)
  vcan0  401   [6]  22 00 3D 99 1A 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 34,
    MODULE_VOLTAGE_34: 39229,
    MODULE_TEMP_34: 23066
)
  vcan0  401   [6]  23 00 59 99 5C 5A ::
BATTERY_VT(
    BATTERY_VT_INDEX: 35,
    MODULE_VOLTAGE_35: 39257,
    MODULE_TEMP_35: 23132
)
"""

        stdout = StringIO()

        with patch('sys.stdin', StringIO(input_data)):
            with patch('sys.stdout', stdout):
                with patch('sys.argv', argv):
                    cantools._main()
                    actual_output = stdout.getvalue()
                    self.assertEqual(actual_output, expected_output)

    def test_decode_single_line_muxed_data(self):
        argv = [
            'cantools',
            'decode',
            '--single-line',
            'tests/files/dbc/msxii_system_can.dbc'
        ]

        input_data = """\
  vcan0  401   [6]  00 00 98 98 0B 00
  vcan0  401   [6]  01 00 9C 98 0A 00
  vcan0  401   [6]  02 00 B5 98 0A 00
  vcan0  401   [6]  03 00 9D 98 0A 00
  vcan0  401   [6]  04 00 CB 98 0B 00
  vcan0  401   [6]  05 00 C5 98 0B 00
  vcan0  401   [6]  06 00 35 9A EA 59
  vcan0  401   [6]  07 00 B1 98 FA 59
  vcan0  401   [6]  08 00 A5 98 0B 00
  vcan0  401   [6]  09 00 73 99 0C 00
  vcan0  401   [6]  0A 00 66 98 0B 00
  vcan0  401   [6]  0B 00 65 96 0B 00
  vcan0  401   [6]  0C 00 72 99 B3 5A
  vcan0  401   [6]  0D 00 04 99 9D 5A
  vcan0  401   [6]  0E 00 F8 9A C4 5A
  vcan0  401   [6]  0F 00 3B 9C 89 5A
  vcan0  401   [6]  10 00 8E 9A DE 5A
  vcan0  401   [6]  11 00 E8 9B DE 5A
  vcan0  401   [6]  12 00 D5 99 C9 59
  vcan0  401   [6]  13 00 EE 99 0D 5A
  vcan0  401   [6]  14 00 83 99 02 5A
  vcan0  401   [6]  15 00 97 99 12 5A
  vcan0  401   [6]  16 00 F6 99 0C 5A
  vcan0  401   [6]  17 00 0E 9B C4 59
  vcan0  401   [6]  18 00 68 9A 42 5A
  vcan0  401   [6]  19 00 83 99 22 5A
  vcan0  401   [6]  1A 00 85 99 3D 5A
  vcan0  401   [6]  1B 00 EF 99 2F 5A
  vcan0  401   [6]  1C 00 7E 99 50 5A
  vcan0  401   [6]  1D 00 39 9A 21 5A
  vcan0  401   [6]  1E 00 44 99 F9 59
  vcan0  401   [6]  1F 00 60 99 1B 5A
  vcan0  401   [6]  20 00 42 99 0A 5A
  vcan0  401   [6]  21 00 C3 9A 33 5A
  vcan0  401   [6]  22 00 3D 99 1A 5A
  vcan0  401   [6]  23 00 59 99 5C 5A
"""

        expected_output = """\
  vcan0  401   [6]  00 00 98 98 0B 00 :: BATTERY_VT(BATTERY_VT_INDEX: 0, MODULE_VOLTAGE_00: 39064, MODULE_TEMP_00: 11)
  vcan0  401   [6]  01 00 9C 98 0A 00 :: BATTERY_VT(BATTERY_VT_INDEX: 1, MODULE_VOLTAGE_01: 39068, MODULE_TEMP_01: 10)
  vcan0  401   [6]  02 00 B5 98 0A 00 :: BATTERY_VT(BATTERY_VT_INDEX: 2, MODULE_VOLTAGE_02: 39093, MODULE_TEMP_02: 10)
  vcan0  401   [6]  03 00 9D 98 0A 00 :: BATTERY_VT(BATTERY_VT_INDEX: 3, MODULE_VOLTAGE_03: 39069, MODULE_TEMP_03: 10)
  vcan0  401   [6]  04 00 CB 98 0B 00 :: BATTERY_VT(BATTERY_VT_INDEX: 4, MODULE_VOLTAGE_04: 39115, MODULE_TEMP_04: 11)
  vcan0  401   [6]  05 00 C5 98 0B 00 :: BATTERY_VT(BATTERY_VT_INDEX: 5, MODULE_VOLTAGE_05: 39109, MODULE_TEMP_05: 11)
  vcan0  401   [6]  06 00 35 9A EA 59 :: BATTERY_VT(BATTERY_VT_INDEX: 6, MODULE_VOLTAGE_06: 39477, MODULE_TEMP_06: 23018)
  vcan0  401   [6]  07 00 B1 98 FA 59 :: BATTERY_VT(BATTERY_VT_INDEX: 7, MODULE_VOLTAGE_07: 39089, MODULE_TEMP_07: 23034)
  vcan0  401   [6]  08 00 A5 98 0B 00 :: BATTERY_VT(BATTERY_VT_INDEX: 8, MODULE_VOLTAGE_08: 39077, MODULE_TEMP_08: 11)
  vcan0  401   [6]  09 00 73 99 0C 00 :: BATTERY_VT(BATTERY_VT_INDEX: 9, MODULE_VOLTAGE_09: 39283, MODULE_TEMP_09: 12)
  vcan0  401   [6]  0A 00 66 98 0B 00 :: BATTERY_VT(BATTERY_VT_INDEX: 10, MODULE_VOLTAGE_10: 39014, MODULE_TEMP_10: 11)
  vcan0  401   [6]  0B 00 65 96 0B 00 :: BATTERY_VT(BATTERY_VT_INDEX: 11, MODULE_VOLTAGE_11: 38501, MODULE_TEMP_11: 11)
  vcan0  401   [6]  0C 00 72 99 B3 5A :: BATTERY_VT(BATTERY_VT_INDEX: 12, MODULE_VOLTAGE_12: 39282, MODULE_TEMP_12: 23219)
  vcan0  401   [6]  0D 00 04 99 9D 5A :: BATTERY_VT(BATTERY_VT_INDEX: 13, MODULE_VOLTAGE_13: 39172, MODULE_TEMP_13: 23197)
  vcan0  401   [6]  0E 00 F8 9A C4 5A :: BATTERY_VT(BATTERY_VT_INDEX: 14, MODULE_VOLTAGE_14: 39672, MODULE_TEMP_14: 23236)
  vcan0  401   [6]  0F 00 3B 9C 89 5A :: BATTERY_VT(BATTERY_VT_INDEX: 15, MODULE_VOLTAGE_15: 39995, MODULE_TEMP_15: 23177)
  vcan0  401   [6]  10 00 8E 9A DE 5A :: BATTERY_VT(BATTERY_VT_INDEX: 16, MODULE_VOLTAGE_16: 39566, MODULE_TEMP_16: 23262)
  vcan0  401   [6]  11 00 E8 9B DE 5A :: BATTERY_VT(BATTERY_VT_INDEX: 17, MODULE_VOLTAGE_17: 39912, MODULE_TEMP_17: 23262)
  vcan0  401   [6]  12 00 D5 99 C9 59 :: BATTERY_VT(BATTERY_VT_INDEX: 18, MODULE_VOLTAGE_18: 39381, MODULE_TEMP_18: 22985)
  vcan0  401   [6]  13 00 EE 99 0D 5A :: BATTERY_VT(BATTERY_VT_INDEX: 19, MODULE_VOLTAGE_19: 39406, MODULE_TEMP_19: 23053)
  vcan0  401   [6]  14 00 83 99 02 5A :: BATTERY_VT(BATTERY_VT_INDEX: 20, MODULE_VOLTAGE_20: 39299, MODULE_TEMP_20: 23042)
  vcan0  401   [6]  15 00 97 99 12 5A :: BATTERY_VT(BATTERY_VT_INDEX: 21, MODULE_VOLTAGE_21: 39319, MODULE_TEMP_21: 23058)
  vcan0  401   [6]  16 00 F6 99 0C 5A :: BATTERY_VT(BATTERY_VT_INDEX: 22, MODULE_VOLTAGE_22: 39414, MODULE_TEMP_22: 23052)
  vcan0  401   [6]  17 00 0E 9B C4 59 :: BATTERY_VT(BATTERY_VT_INDEX: 23, MODULE_VOLTAGE_23: 39694, MODULE_TEMP_23: 22980)
  vcan0  401   [6]  18 00 68 9A 42 5A :: BATTERY_VT(BATTERY_VT_INDEX: 24, MODULE_VOLTAGE_24: 39528, MODULE_TEMP_24: 23106)
  vcan0  401   [6]  19 00 83 99 22 5A :: BATTERY_VT(BATTERY_VT_INDEX: 25, MODULE_VOLTAGE_25: 39299, MODULE_TEMP_25: 23074)
  vcan0  401   [6]  1A 00 85 99 3D 5A :: BATTERY_VT(BATTERY_VT_INDEX: 26, MODULE_VOLTAGE_26: 39301, MODULE_TEMP_26: 23101)
  vcan0  401   [6]  1B 00 EF 99 2F 5A :: BATTERY_VT(BATTERY_VT_INDEX: 27, MODULE_VOLTAGE_27: 39407, MODULE_TEMP_27: 23087)
  vcan0  401   [6]  1C 00 7E 99 50 5A :: BATTERY_VT(BATTERY_VT_INDEX: 28, MODULE_VOLTAGE_28: 39294, MODULE_TEMP_28: 23120)
  vcan0  401   [6]  1D 00 39 9A 21 5A :: BATTERY_VT(BATTERY_VT_INDEX: 29, MODULE_VOLTAGE_29: 39481, MODULE_TEMP_29: 23073)
  vcan0  401   [6]  1E 00 44 99 F9 59 :: BATTERY_VT(BATTERY_VT_INDEX: 30, MODULE_VOLTAGE_30: 39236, MODULE_TEMP_30: 23033)
  vcan0  401   [6]  1F 00 60 99 1B 5A :: BATTERY_VT(BATTERY_VT_INDEX: 31, MODULE_VOLTAGE_31: 39264, MODULE_TEMP_31: 23067)
  vcan0  401   [6]  20 00 42 99 0A 5A :: BATTERY_VT(BATTERY_VT_INDEX: 32, MODULE_VOLTAGE_32: 39234, MODULE_TEMP_32: 23050)
  vcan0  401   [6]  21 00 C3 9A 33 5A :: BATTERY_VT(BATTERY_VT_INDEX: 33, MODULE_VOLTAGE_33: 39619, MODULE_TEMP_33: 23091)
  vcan0  401   [6]  22 00 3D 99 1A 5A :: BATTERY_VT(BATTERY_VT_INDEX: 34, MODULE_VOLTAGE_34: 39229, MODULE_TEMP_34: 23066)
  vcan0  401   [6]  23 00 59 99 5C 5A :: BATTERY_VT(BATTERY_VT_INDEX: 35, MODULE_VOLTAGE_35: 39257, MODULE_TEMP_35: 23132)
"""

        stdout = StringIO()

        with patch('sys.stdin', StringIO(input_data)):
            with patch('sys.stdout', stdout):
                with patch('sys.argv', argv):
                    cantools._main()
                    actual_output = stdout.getvalue()
                    self.assertEqual(actual_output, expected_output)

    def test_dump(self):
        argv = [
            'cantools',
            'dump',
            'tests/files/dbc/motohawk.dbc'
        ]

        expected_output = """\
================================= Messages =================================

  ------------------------------------------------------------------------

  Name:           ExampleMessage
  Id:             0x1f0
  Length:         8 bytes
  Cycle time:     - ms
  Senders:        PCM1
  Layout:

                          Bit

             7   6   5   4   3   2   1   0
           +---+---+---+---+---+---+---+---+
         0 |<-x|<---------------------x|<--|
           +---+---+---+---+---+---+---+---+
             |                       +-- AverageRadius
             +-- Enable
           +---+---+---+---+---+---+---+---+
         1 |-------------------------------|
           +---+---+---+---+---+---+---+---+
         2 |----------x|   |   |   |   |   |
     B     +---+---+---+---+---+---+---+---+
     y               +-- Temperature
     t     +---+---+---+---+---+---+---+---+
     e   3 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         4 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         5 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         6 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         7 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+

  Signal tree:

    -- {root}
       +-- Enable
       +-- AverageRadius
       +-- Temperature

  Signal choices:

    Enable
        0 Disabled
        1 Enabled

  ------------------------------------------------------------------------
"""

        stdout = StringIO()

        with patch('sys.stdout', stdout):
            with patch('sys.argv', argv):
                cantools._main()
                actual_output = stdout.getvalue()
                self.assertEqual(actual_output, expected_output)

    @with_fake_screen_width(screen_width=80)
    def test_dump_with_comments(self):
        argv = [
            'cantools',
            'dump',
            '--with-comments',
            'tests/files/dbc/motohawk_with_comments.dbc'
        ]

        expected_output = """\
================================= Messages =================================

  ------------------------------------------------------------------------

  Name:           ExampleMessage
  Id:             0x1f0
  Length:         8 bytes
  Cycle time:     - ms
  Senders:        PCM1
  Layout:

                          Bit

             7   6   5   4   3   2   1   0
           +---+---+---+---+---+---+---+---+
         0 |<-x|<---------------------x|<--|
           +---+---+---+---+---+---+---+---+
             |                       +-- AverageRadius
             +-- Enable
           +---+---+---+---+---+---+---+---+
         1 |-------------------------------|
           +---+---+---+---+---+---+---+---+
         2 |----------x|   |   |   |   |   |
     B     +---+---+---+---+---+---+---+---+
     y               +-- Temperature
     t     +---+---+---+---+---+---+---+---+
     e   3 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         4 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         5 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         6 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         7 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+

  Signal tree:

    -- {root}
       +-- Enable [94mEnable signal comment [-][0m
       +-- AverageRadius [94mAverageRadius signal comment [m][0m
       +-- Temperature [94mTemperature with a really long and complicated comment
                       that probably require many many lines in a decently wide
                       terminal [degK][0m

  Signal choices:

    Enable
        0 Disabled
        1 Enabled

  ------------------------------------------------------------------------
"""

        stdout = StringIO()

        with patch('sys.stdout', stdout):
            with patch('sys.argv', argv):
                cantools._main()
                actual_output = stdout.getvalue()
                self.assertEqual(actual_output, expected_output)

    @with_fake_screen_width(screen_width=80)
    def test_dump_with_comments_mux(self):
        argv = [
            'cantools',
            'dump',
            '--with-comments',
            'tests/files/dbc/bus_comment.dbc'
        ]

        expected_output = """\
================================= Messages =================================

  ------------------------------------------------------------------------

  Name:           Message1
  Id:             0x123456
      Priority:       0
      PGN:            0x01200
      Source:         0x56
      Destination:    0x34
      Format:         PDU 1
  Length:         8 bytes
  Cycle time:     - ms
  Senders:        -
  Layout:

                          Bit

             7   6   5   4   3   2   1   0
           +---+---+---+---+---+---+---+---+
         0 |<---------------------x|   |   |
           +---+---+---+---+---+---+---+---+
             +-- Multiplexor
           +---+---+---+---+---+---+---+---+
         1 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         2 |<-x|   |   |   |<-x|<-x|   |   |
           +---+---+---+---+---+---+---+---+
             |               |   +-- BIT_J
             |               +-- BIT_C
             +-- BIT_G
           +---+---+---+---+---+---+---+---+
         3 |   |   |<-x|<-x|   |<-x|   |<-x|
     B     +---+---+---+---+---+---+---+---+
     y               |   |       |       +-- BIT_L
     t               |   |       +-- BIT_A
     e               |   +-- BIT_K
                     +-- BIT_E
           +---+---+---+---+---+---+---+---+
         4 |<-x|<-x|   |   |   |   |<-x|<-x|
           +---+---+---+---+---+---+---+---+
             |   |                   |   +-- BIT_D
             |   |                   +-- BIT_B
             |   +-- BIT_H
             +-- BIT_F
           +---+---+---+---+---+---+---+---+
         5 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         6 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         7 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+

  Signal tree:

    -- {root}
       +-- Multiplexor [94mDefines data content for response messages.[0m
           +-- 8
           |   +-- BIT_J
           |   +-- BIT_C
           |   +-- BIT_G
           |   +-- BIT_L
           +-- 16
           |   +-- BIT_J
           |   +-- BIT_C
           |   +-- BIT_G
           |   +-- BIT_L
           +-- 24
               +-- BIT_J
               +-- BIT_C
               +-- BIT_G
               +-- BIT_L
               +-- BIT_A
               +-- BIT_K
               +-- BIT_E
               +-- BIT_D
               +-- BIT_B
               +-- BIT_H
               +-- BIT_F

  ------------------------------------------------------------------------
"""

        stdout = StringIO()

        with patch('sys.stdout', stdout):
            with patch('sys.argv', argv):
                cantools._main()
                actual_output = stdout.getvalue()
                self.assertEqual(actual_output, expected_output)

    def test_dump_no_sender(self):
        argv = [
            'cantools',
            'dump',
            '--no-strict',
            'tests/files/dbc/no_sender.dbc'
        ]

        expected_output = """\
================================= Messages =================================

  ------------------------------------------------------------------------

  Name:           Foo
  Id:             0x1d8
  Length:         1 bytes
  Cycle time:     - ms
  Senders:        -
  Layout:

                          Bit

             7   6   5   4   3   2   1   0
           +---+---+---+---+---+---+---+---+
     B   0 |<-----------------------------x|
     y     +---+---+---+---+---+---+---+---+
     t       +-- signal_without_sender
     e

  Signal tree:

    -- {root}
       +-- signal_without_sender

  ------------------------------------------------------------------------
"""

        stdout = StringIO()

        with patch('sys.stdout', stdout):
            with patch('sys.argv', argv):
                cantools._main()
                actual_output = stdout.getvalue()
                self.assertEqual(actual_output, expected_output)

    def test_dump_signal_choices(self):
        argv = [
            'cantools',
            'dump',
            '--prune',
            'tests/files/dbc/dump_signal_choices.dbc'
        ]

        expected_output = """\
================================= Messages =================================

  ------------------------------------------------------------------------

  Name:           Message0
  Id:             0x400
  Length:         8 bytes
  Cycle time:     - ms
  Senders:        Node0
  Layout:

                          Bit

             7   6   5   4   3   2   1   0
           +---+---+---+---+---+---+---+---+
         0 |   |   |   |<---------x|<-----x|
           +---+---+---+---+---+---+---+---+
                         |           +-- FooSignal
                         +-- BarSignal
           +---+---+---+---+---+---+---+---+
         1 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
     B   2 |   |   |   |   |   |   |   |   |
     y     +---+---+---+---+---+---+---+---+
     t   3 |   |   |   |   |   |   |   |   |
     e     +---+---+---+---+---+---+---+---+
         4 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         5 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         6 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         7 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+

  Signal tree:

    -- {root}
       +-- FooSignal
       +-- BarSignal

  Signal choices:

    FooSignal
        0 A
        1 B
        2 C
        3 D

    BarSignal
        0 A
        1 B
        2 C
        3 D
        4 E
        5 F
        6 G
        7 H

  ------------------------------------------------------------------------
"""

        stdout = StringIO()

        with patch('sys.stdout', stdout):
            with patch('sys.argv', argv):
                cantools._main()
                actual_output = stdout.getvalue()
                self.assertEqual(actual_output, expected_output)

    def test_dump_j1939(self):
        argv = [
            'cantools',
            'dump',
            'tests/files/dbc/j1939.dbc'
        ]

        expected_output = """\
================================= Messages =================================

  ------------------------------------------------------------------------

  Name:           Message1
  Id:             0x15340201
      Priority:       5
      PGN:            0x13400
      Source:         0x01
      Destination:    0x02
      Format:         PDU 1
  Length:         8 bytes
  Cycle time:     - ms
  Senders:        Node1
  Layout:

                          Bit

             7   6   5   4   3   2   1   0
           +---+---+---+---+---+---+---+---+
         0 |<-----------------------------x|
           +---+---+---+---+---+---+---+---+
             +-- Signal1
           +---+---+---+---+---+---+---+---+
         1 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
     B   2 |   |   |   |   |   |   |   |   |
     y     +---+---+---+---+---+---+---+---+
     t   3 |   |   |   |   |   |   |   |   |
     e     +---+---+---+---+---+---+---+---+
         4 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         5 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         6 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         7 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+

  Signal tree:

    -- {root}
       +-- Signal1

  ------------------------------------------------------------------------

  Name:           Message2
  Id:             0x15f01002
      Priority:       5
      PGN:            0x1f010
      Source:         0x02
      Destination:    All
      Format:         PDU 2
  Length:         8 bytes
  Cycle time:     - ms
  Senders:        Node2
  Layout:

                          Bit

             7   6   5   4   3   2   1   0
           +---+---+---+---+---+---+---+---+
         0 |<-----------------------------x|
           +---+---+---+---+---+---+---+---+
             +-- Signal2
           +---+---+---+---+---+---+---+---+
         1 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
     B   2 |   |   |   |   |   |   |   |   |
     y     +---+---+---+---+---+---+---+---+
     t   3 |   |   |   |   |   |   |   |   |
     e     +---+---+---+---+---+---+---+---+
         4 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         5 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         6 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+
         7 |   |   |   |   |   |   |   |   |
           +---+---+---+---+---+---+---+---+

  Signal tree:

    -- {root}
       +-- Signal2

  ------------------------------------------------------------------------
"""

        stdout = StringIO()

        with patch('sys.stdout', stdout):
            with patch('sys.argv', argv):
                cantools._main()
                actual_output = stdout.getvalue()
                self.assertEqual(actual_output, expected_output)

    def test_convert(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # DBC to KCD.
            kcd_out_path = os.path.join(tmpdir, 'test_command_line_convert.kcd')
            argv = [
                'cantools',
                'convert',
                'tests/files/dbc/motohawk.dbc',
                kcd_out_path
            ]

            with patch('sys.argv', argv):
                cantools._main()

            db = cantools.database.Database()
            db.add_kcd_file(kcd_out_path)
            self.assertEqual(db.version, '1.0')

            # KCD to DBC.
            dbc_out_path = os.path.join(tmpdir, 'test_command_line_convert.dbc')
            argv = [
                'cantools',
                'convert',
                kcd_out_path,
                dbc_out_path
            ]

            with patch('sys.argv', argv):
                cantools._main()

            db = cantools.database.Database()
            db.add_dbc_file(dbc_out_path)
            self.assertEqual(db.version, '1.0')

    def test_convert_bad_outfile(self):
        argv = [
            'cantools',
            'convert',
            'tests/files/dbc/motohawk.dbc',
            'test_command_line_convert.foo'
        ]

        with patch('sys.argv', argv):
            with self.assertRaises(SystemExit) as cm:
                cantools._main()

            self.assertEqual(
                str(cm.exception),
                "error: Unsupported output database format 'foo'.")

    def test_generate_c_source(self):
        databases = [
            'motohawk',
            'padding_bit_order',
            'vehicle',
            'open_actuator',
            'floating_point',
            'floating_point_use_float',
            'no_signals',
            'choices',
            'multiplex',
            'multiplex_2',
            'signed',
            ('CamelCaseEmpty', 'camel_case_empty'),
            'abs'
        ]

        with tempfile.TemporaryDirectory() as _tmpdir:
            tmpdir = Path(_tmpdir)

            for database in databases:
                if isinstance(database, tuple):
                    database, basename = database
                else:
                    basename = database

                argv = [
                    'cantools',
                    'generate_c_source',
                    f'tests/files/dbc/{database}.dbc',
                    '-o',
                    str(tmpdir),
                ]
                if database == 'floating_point_use_float':
                    argv.append('--use-float')

                with patch('sys.argv', argv), warnings.catch_warnings(record=True) as w:
                    cantools._main()

                    if database == 'floating_point_use_float':
                        assert str(w[-1].message) == (
                            "User selected `--use-float`, but database contains "
                            "signal with data type `double`: \"Message1::Signal1\"")

                database_h = basename + '.h'
                database_c = basename + '.c'
                fuzzer_c = basename + '_fuzzer.c'
                fuzzer_mk = basename + '_fuzzer.mk'

                self.assert_files_equal(tmpdir / database_h,
                                        'tests/files/c_source/' + database_h)
                self.assert_files_equal(tmpdir / database_c,
                                        'tests/files/c_source/' + database_c)
                self.assertFalse((tmpdir / fuzzer_c).exists())
                self.assertFalse((tmpdir / fuzzer_mk).exists())

    def test_generate_c_source_no_signal_encode_decode(self):
        databases = [
            'motohawk',
            'open_actuator'
        ]

        with tempfile.TemporaryDirectory() as _tmpdir:
            tmpdir = Path(_tmpdir)

            for database in databases:
                argv = [
                    'cantools',
                    'generate_c_source',
                    '--no-floating-point-numbers',
                    f'tests/files/dbc/{database}.dbc',
                    '-o',
                    str(tmpdir),
                ]

                database_h = database + '.h'
                database_c = database + '.c'
                expected_database_h = database + '_no_floating_point_numbers.h'
                expected_database_c = database + '_no_floating_point_numbers.c'

                with patch('sys.argv', argv):
                    cantools._main()

                self.assert_files_equal(
                    tmpdir / database_h,
                    'tests/files/c_source/' + expected_database_h)
                self.assert_files_equal(
                    tmpdir / database_c,
                    'tests/files/c_source/' + expected_database_c)

    def test_generate_c_source_sender_node_no_signal_encode_decode(self):
        databases = [
            'motohawk',
            'open_actuator'
        ]
        nodes = [
            'PCM1',
            'Actuator'
        ]

        with tempfile.TemporaryDirectory() as _tmpdir:
            tmpdir = Path(_tmpdir)

            for database, node in zip(databases, nodes):
                argv = [
                    'cantools',
                    'generate_c_source',
                    '--no-floating-point-numbers',
                    '--node', node,
                    f'tests/files/dbc/{database}.dbc',
                    '-o',
                    str(tmpdir),
                ]

                database_h = database + '.h'
                database_c = database + '.c'
                expected_database_h = database + '_sender_node_no_floating_point_numbers.h'
                expected_database_c = database + '_sender_node_no_floating_point_numbers.c'

                with patch('sys.argv', argv):
                    cantools._main()

                self.assert_files_equal(tmpdir / database_h,
                                        'tests/files/c_source/' + expected_database_h)
                self.assert_files_equal(tmpdir / database_c,
                                        'tests/files/c_source/' + expected_database_c)

    def test_generate_c_source_database_name(self):
        databases = [
            'motohawk',
        ]

        with tempfile.TemporaryDirectory() as _tmpdir:
            tmpdir = Path(_tmpdir)

            for database in databases:
                argv = [
                    'cantools',
                    'generate_c_source',
                    '--database-name', 'my_database_name',
                    f'tests/files/dbc/{database}.dbc',
                    '-o',
                    str(tmpdir),
                ]

                database_h = 'my_database_name.h'
                database_c = 'my_database_name.c'

                with patch('sys.argv', argv):
                    cantools._main()

                self.assert_files_equal(tmpdir / database_h,
                                        'tests/files/c_source/' + database_h)
                self.assert_files_equal(tmpdir / database_c,
                                        'tests/files/c_source/' + database_c)

    def test_generate_c_source_working_directory(self):
        database = 'motohawk'

        argv = [
            'cantools',
            'generate_c_source',
            f'tests/files/dbc/{database}.dbc'
        ]

        database_h = database + '.h'
        database_c = database + '.c'

        with patch('sys.argv', argv):
            cantools._main()

        self.assert_files_equal(database_h,
                                'tests/files/c_source/' + os.path.basename(database_h))
        self.assert_files_equal(database_c,
                                'tests/files/c_source/' + os.path.basename(database_c))

        if os.path.exists(database_h):
            os.remove(database_h)

        if os.path.exists(database_c):
            os.remove(database_c)

    def test_generate_c_source_bit_fields(self):
        databases = [
            'motohawk',
            'floating_point',
            'signed'
        ]

        with tempfile.TemporaryDirectory() as _tmpdir:
            tmpdir = Path(_tmpdir)

            for database in databases:
                argv = [
                    'cantools',
                    'generate_c_source',
                    '--bit-fields',
                    '--database-name', f'{database}_bit_fields',
                    f'tests/files/dbc/{database}.dbc',
                    '-o',
                    str(tmpdir),
                ]

                database_h = database + '_bit_fields.h'
                database_c = database + '_bit_fields.c'

                with patch('sys.argv', argv):
                    cantools._main()

                self.assert_files_equal(tmpdir / database_h,
                                        'tests/files/c_source/' + database_h)
                self.assert_files_equal(tmpdir / database_c,
                                        'tests/files/c_source/' + database_c)

    def test_generate_c_source_sender_node(self):
        databases = [
            'motohawk',
            'open_actuator'
        ]
        nodes = [
            'PCM1',
            'Actuator'
        ]

        with tempfile.TemporaryDirectory() as _tmpdir:
            tmpdir = Path(_tmpdir)

            for database, node in zip(databases, nodes):
                argv = [
                    'cantools',
                    'generate_c_source',
                    '--node', node,
                    f'tests/files/dbc/{database}.dbc',
                    '-o',
                    str(tmpdir),
                ]

                database_h = database + '.h'
                database_c = database + '.c'
                expected_database_h = database + '_sender_node.h'
                expected_database_c = database + '_sender_node.c'

                with patch('sys.argv', argv):
                    cantools._main()

                self.assert_files_equal(tmpdir / database_h,
                                        'tests/files/c_source/' + expected_database_h)
                self.assert_files_equal(tmpdir / database_c,
                                        'tests/files/c_source/' + expected_database_c)

    def test_generate_c_source_generate_fuzzer(self):
        with tempfile.TemporaryDirectory() as _tmpdir:
            tmpdir = Path(_tmpdir)

            argv = [
                'cantools',
                'generate_c_source',
                '--generate-fuzzer',
                'tests/files/dbc/multiplex_2.dbc',
                '-o',
                str(tmpdir),
            ]

            database_h = 'multiplex_2.h'
            database_c = 'multiplex_2.c'
            fuzzer_c = 'multiplex_2_fuzzer.c'
            fuzzer_mk = 'multiplex_2_fuzzer.mk'

            with patch('sys.argv', argv):
                cantools._main()

            self.assert_files_equal(tmpdir / database_h,
                                    'tests/files/c_source/' + database_h)
            self.assert_files_equal(tmpdir / database_c,
                                    'tests/files/c_source/' + database_c)
            self.assert_files_equal(tmpdir / fuzzer_c,
                                    'tests/files/c_source/' + fuzzer_c)
            self.assert_files_equal(tmpdir / fuzzer_mk,
                                    'tests/files/c_source/' + fuzzer_mk)

    def test_generate_c_source_sym(self):
        databases = [
            ('min-max-only-6.0', 'min_max_only_6_0'),
            ('letter-terminated-can-id-6.0', 'letter_terminated_can_id_6_0')
        ]

        with tempfile.TemporaryDirectory() as _tmpdir:
            tmpdir = Path(_tmpdir)

            for database in databases:
                if isinstance(database, tuple):
                    database, basename = database
                else:
                    basename = database

                argv = [
                    'cantools',
                    'generate_c_source',
                    f'tests/files/sym/{database}.sym',
                    '-o',
                    str(tmpdir),
                ]

                database_h = basename + '.h'
                database_c = basename + '.c'
                fuzzer_c = basename + '_fuzzer.c'
                fuzzer_mk = basename + '_fuzzer.mk'

                with patch('sys.argv', argv):
                    cantools._main()

                self.assert_files_equal(tmpdir / database_h,
                                        'tests/files/c_source/' + database_h)
                self.assert_files_equal(tmpdir / database_c,
                                        'tests/files/c_source/' + database_c)
                self.assertFalse((tmpdir / fuzzer_c).exists())
                self.assertFalse((tmpdir / fuzzer_mk).exists())


if __name__ == '__main__':
    unittest.main()
