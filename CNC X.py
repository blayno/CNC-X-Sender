import sys
import time
import re
import os
import json
import serial
import serial.tools.list_ports
import numpy as np

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtMultimedia import QSound
import pyqtgraph as pg
import pyqtgraph.opengl as gl


# =========================================================
# MAD HAT CNC SENDER
# =========================================================

APP_NAME = "MAD HAT CNC SENDER"
APP_VERSION = "V2.0"

LOGO_PATH = "Assets/madhat-cnc-logo.png"

BAUD_RATES = [
    "115200",
    "250000",
    "57600",
    "38400",
    "19200",
    "9600"
]


# =========================================================
# DARK MAD HAT STYLE
# =========================================================

APP_STYLE = """
QWidget {
    background: #111111;
    color: #eeeeee;
    font-family: Arial;
    font-size: 10pt;
}

QMainWindow {
    background: #0d0d0d;
}

QFrame#Header {
    background: #181818;
    border-bottom: 2px solid #f0a500;
}

QFrame#Card {
    background: #1a1a1a;
    border: 1px solid #303030;
    border-radius: 6px;
}

QFrame#Card:hover {
    border: 1px solid #444444;
}

QLabel#Brand {
    color: #f0a500;
    font-size: 21pt;
    font-weight: bold;
}

QLabel#BrandSub {
    color: #aaaaaa;
    font-size: 8pt;
}

QLabel#SectionTitle {
    color: #f0a500;
    font-size: 9pt;
    font-weight: bold;
}

QLabel#SmallLabel {
    color: #888888;
    font-size: 8pt;
}

QLabel#BigDRO {
    color: #ffffff;
    font-family: Consolas;
    font-size: 19pt;
    font-weight: bold;
}

QLabel#Status {
    color: #f0a500;
    font-size: 12pt;
    font-weight: bold;
}

QLabel#Value {
    color: #eeeeee;
    font-family: Consolas;
    font-size: 11pt;
}

QPushButton {
    background: #242424;
    border: 1px solid #3b3b3b;
    border-radius: 5px;
    padding: 7px;
    color: #eeeeee;
    font-weight: bold;
}

QPushButton:hover {
    background: #303030;
    border: 1px solid #f0a500;
}

QPushButton:pressed {
    background: #f0a500;
    color: #111111;
}

QPushButton:disabled {
    background: #171717;
    color: #555555;
    border: 1px solid #242424;
}

QPushButton#Play {
    background: #f0a500;
    color: #111111;
    font-size: 12pt;
}

QPushButton#Pause {
    background: #805800;
    color: #ffffff;
    font-size: 11pt;
}

QPushButton#Stop {
    background: #662222;
    color: #ffffff;
    font-size: 11pt;
}

QPushButton#Stop:hover {
    background: #8a2929;
}

QPushButton#Emergency {
    background: #8b0000;
    color: #ffffff;
    font-size: 11pt;
}

QPushButton#Emergency:hover {
    background: #b00000;
}

QPushButton#Jog {
    min-width: 62px;
    min-height: 42px;
    font-size: 11pt;
}

QPushButton#Zero {
    color: #f0a500;
}

QPushButton#Home {
    color: #f0a500;
}

QPushButton#Danger {
    color: #ff7777;
}

QLineEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox {
    background: #151515;
    border: 1px solid #383838;
    border-radius: 4px;
    padding: 6px;
    color: #eeeeee;
}

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QDoubleSpinBox:focus {
    border: 1px solid #f0a500;
}

QTextEdit,
QPlainTextEdit {
    background: #0a0a0a;
    border: 1px solid #303030;
    color: #dddddd;
    font-family: Consolas;
    font-size: 9pt;
}

QProgressBar {
    background: #0b0b0b;
    border: 1px solid #333333;
    border-radius: 5px;
    height: 15px;
    text-align: center;
    color: #ffffff;
}

QProgressBar::chunk {
    background: #f0a500;
    border-radius: 4px;
}

QSlider::groove:horizontal {
    height: 5px;
    background: #333333;
}

QSlider::handle:horizontal {
    background: #f0a500;
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}

QScrollArea {
    background: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}

QScrollBar:vertical {
    background: #151515;
    width: 10px;
}

QScrollBar::handle:vertical {
    background: #444444;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #f0a500;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QTabWidget::pane {
    border: 1px solid #303030;
    background: #111111;
}

QTabBar::tab {
    background: #202020;
    color: #999999;
    padding: 7px 15px;
    border: 1px solid #303030;
}

QTabBar::tab:selected {
    color: #f0a500;
    background: #181818;
}

QGroupBox {
    border: 1px solid #303030;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: #f0a500;
}

QTableWidget {
    background: #0a0a0a;
    alternate-background-color: #141414;
    border: 1px solid #303030;
    gridline-color: #303030;
    color: #dddddd;
}

QTableWidget::item:selected {
    background: #f0a500;
    color: #111111;
}

QHeaderView::section {
    background: #202020;
    color: #f0a500;
    border: 1px solid #303030;
    padding: 4px;
    font-weight: bold;
}
"""


# =========================================================
# CNC SENDER THREAD
# =========================================================

class SenderThread(QtCore.QThread):

    log_signal = QtCore.pyqtSignal(str)
    progress_signal = QtCore.pyqtSignal(int)
    line_signal = QtCore.pyqtSignal(int)
    feed_signal = QtCore.pyqtSignal(float)
    speed_signal = QtCore.pyqtSignal(float)
    status_signal = QtCore.pyqtSignal(float, float, float)
    machine_state_signal = QtCore.pyqtSignal(str)
    done_signal = QtCore.pyqtSignal()
    stopped_signal = QtCore.pyqtSignal()
    error_signal = QtCore.pyqtSignal(str)

    RX_BUFFER = 128
    SAFETY = 10

    def __init__(self, ser, gcode_lines):

        super().__init__()

        self.ser = ser
        self.gcode_lines = gcode_lines

        self._stop = False
        self._pause_requested = False

        self.in_flight = []
        self.bytes_in_flight = 0
        self.current_index = -1

    def stop(self):

        self._stop = True

    def run(self):

        idx = 0
        total = len(self.gcode_lines)

        last_status = time.time()

        while not self._stop:

            while (
                idx < total
                and
                self.bytes_in_flight < self.RX_BUFFER - self.SAFETY
                and
                not self._stop
            ):

                raw = self.gcode_lines[idx].strip()

                line_number = idx

                idx += 1

                if not raw:
                    continue

                raw = re.sub(
                    r"\([^)]*\)",
                    "",
                    raw
                )

                raw = raw.split(";")[0].strip()

                if not raw:
                    continue

                clean = re.sub(
                    r"^N\d+\s*",
                    "",
                    raw,
                    flags=re.IGNORECASE
                )

                line = clean + "\n"

                size = len(
                    line.encode(
                        "ascii",
                        errors="ignore"
                    )
                )

                if (
                    self.bytes_in_flight + size
                    >
                    self.RX_BUFFER - self.SAFETY
                ):

                    idx -= 1
                    break

                feed = re.search(
                    r"\bF([-+]?\d*\.?\d+)",
                    clean.upper()
                )

                if feed:

                    self.feed_signal.emit(
                        float(feed.group(1))
                    )

                speed = re.search(
                    r"\bS([-+]?\d*\.?\d+)",
                    clean.upper()
                )

                if speed:

                    self.speed_signal.emit(
                        float(speed.group(1))
                    )

                sent = False

                while (
                    not sent
                    and
                    not self._stop
                ):

                    try:

                        self.ser.write(
                            line.encode()
                        )

                        sent = True

                    except serial.SerialTimeoutException:

                        time.sleep(0.01)

                    except serial.SerialException as e:

                        self.error_signal.emit(
                            f"Serial write error: {e}"
                        )

                        self._stop = True
                        break

                if self._stop:
                    break

                self.in_flight.append(
                    (
                        line_number,
                        size
                    )
                )

                self.bytes_in_flight += size

                self.current_index = line_number

                self.line_signal.emit(
                    line_number
                )

                self.log_signal.emit(
                    f">> N{line_number + 1}: {clean}"
                )

                progress = int(
                    (
                        (line_number + 1)
                        /
                        max(total, 1)
                    )
                    * 100
                )

                self.progress_signal.emit(
                    min(progress, 100)
                )

            try:

                while self.ser.in_waiting:

                    response = (
                        self.ser.readline()
                        .decode(errors="ignore")
                        .strip()
                    )

                    if not response:
                        continue

                    if response.startswith("<"):

                        self.parse_status(
                            response
                        )

                    elif response.lower().startswith("ok"):

                        self.log_signal.emit(
                            f"<< {response}"
                        )

                        if self.in_flight:

                            _, size = self.in_flight.pop(0)

                            self.bytes_in_flight -= size

                    elif response.lower().startswith("error"):

                        self.log_signal.emit(
                            f"<< {response}"
                        )

                        if self.in_flight:

                            _, size = self.in_flight.pop(0)

                            self.bytes_in_flight -= size

                    elif response.lower().startswith("alarm"):

                        self.log_signal.emit(
                            f"<< {response}"
                        )

                    else:

                        self.log_signal.emit(
                            f"<< {response}"
                        )

            except serial.SerialException as e:

                self.error_signal.emit(
                    f"Serial read error: {e}"
                )

                self._stop = True

            if time.time() - last_status >= 0.10:

                try:

                    self.ser.write(
                        b"?"
                    )

                except Exception:
                    pass

                last_status = time.time()

            if (
                idx >= total
                and
                not self.in_flight
            ):

                break

            time.sleep(0.001)

        if self._stop:

            self.log_signal.emit(
                "JOB STOPPED"
            )

            self.stopped_signal.emit()

        else:

            self.progress_signal.emit(100)

            self.log_signal.emit(
                "JOB COMPLETE"
            )

            self.done_signal.emit()

    def parse_status(self, status):

        state = re.match(
            r"<([^|,]+)",
            status
        )

        if state:

            self.machine_state_signal.emit(
                state.group(1)
            )

        mpos = re.search(
            r"MPos:([-0-9.]+),([-0-9.]+),([-0-9.]+)",
            status
        )

        wpos = re.search(
            r"WPos:([-0-9.]+),([-0-9.]+),([-0-9.]+)",
            status
        )

        wco = re.search(
            r"WCO:([-0-9.]+),([-0-9.]+),([-0-9.]+)",
            status
        )

        x = y = z = 0.0

        if wpos:

            x, y, z = map(
                float,
                wpos.groups()
            )

        elif mpos and wco:

            mx, my, mz = map(
                float,
                mpos.groups()
            )

            wx, wy, wz = map(
                float,
                wco.groups()
            )

            x = mx - wx
            y = my - wy
            z = mz - wz

        elif mpos:

            x, y, z = map(
                float,
                mpos.groups()
            )

        self.status_signal.emit(
            x,
            y,
            z
        )

        fs = re.search(
            r"FS:([0-9.]+),([0-9.]+)",
            status
        )

        if fs:

            self.feed_signal.emit(
                float(fs.group(1))
            )

            self.speed_signal.emit(
                float(fs.group(2))
            )




# =========================================================
# AUTOLEVEL WORKER
# =========================================================

class AutoLevelWorker(QtCore.QThread):

    log_signal = QtCore.pyqtSignal(str)

    progress_signal = QtCore.pyqtSignal(int)

    point_signal = QtCore.pyqtSignal(
        int,
        int,
        float,
        float,
        float
    )

    status_signal = QtCore.pyqtSignal(str)

    finished_signal = QtCore.pyqtSignal(object)

    stopped_signal = QtCore.pyqtSignal()

    error_signal = QtCore.pyqtSignal(str)

    def __init__(
        self,
        ser,
        x_min,
        x_max,
        y_min,
        y_max,
        z_min,
        z_max,
        resolution,
        probe_feed,
        z_retract,
        probe_x_offset,
        probe_y_offset,
        probe_z_offset
    ):

        super().__init__()

        self.ser = ser

        self.x_min = float(x_min)
        self.x_max = float(x_max)

        self.y_min = float(y_min)
        self.y_max = float(y_max)

        self.z_min = float(z_min)
        self.z_max = float(z_max)

        self.resolution = float(resolution)

        self.probe_feed = float(
            probe_feed
        )

        self.z_retract = float(
            z_retract
        )

        self.probe_x_offset = float(
            probe_x_offset
        )

        self.probe_y_offset = float(
            probe_y_offset
        )

        self.probe_z_offset = float(
            probe_z_offset
        )

        self._stop_requested = False

        self.points = []

    # =====================================================
    # STOP
    # =====================================================

    def stop(self):

        self._stop_requested = True

        try:

            if self.ser and self.ser.is_open:

                self.ser.write(
                    b"\x18"
                )

                self.ser.flush()

        except Exception:
            pass

    # =====================================================
    # GRID
    # =====================================================

    def build_axis(
        self,
        minimum,
        maximum
    ):

        if maximum <= minimum:

            return []

        values = [
            float(minimum)
        ]

        current = float(minimum)

        while (
            current + self.resolution
            <
            maximum
        ):

            current += self.resolution

            values.append(
                float(current)
            )

        if values[-1] < maximum:

            values.append(
                float(maximum)
            )

        return values

    # =====================================================
    # READ SERIAL
    # =====================================================

    def read_serial_line(self):

        try:

            if not self.ser.in_waiting:

                return None

            response = (
                self.ser.readline()
                .decode(
                    errors="ignore"
                )
                .strip()
            )

            if not response:

                return None

            self.log_signal.emit(
                f"<< {response}"
            )

            return response

        except serial.SerialException as e:

            raise RuntimeError(
                f"Serial read error: {e}"
            )

    # =====================================================
    # SEND NORMAL COMMAND
    # =====================================================

    def send_and_wait(
        self,
        command,
        timeout=30.0
    ):

        if self._stop_requested:

            return False

        try:

            self.ser.write(
                (
                    command.strip()
                    +
                    "\n"
                ).encode()
            )

            self.ser.flush()

        except Exception as e:

            raise RuntimeError(
                f"Serial write error: {e}"
            )

        self.log_signal.emit(
            f">> {command}"
        )

        start_time = time.time()

        while (
            time.time()
            -
            start_time
            <
            timeout
        ):

            if self._stop_requested:

                return False

            response = self.read_serial_line()

            if response is None:

                time.sleep(
                    0.005
                )

                continue

            response_lower = (
                response.lower()
            )

            # -------------------------------------------------
            # ALARM
            # -------------------------------------------------

            if response_lower.startswith(
                "alarm"
            ):

                raise RuntimeError(
                    f"GRBL alarm: {response}"
                )

            # -------------------------------------------------
            # ERROR
            # -------------------------------------------------

            if response_lower.startswith(
                "error"
            ):

                raise RuntimeError(
                    f"GRBL error: {response}"
                )

            # -------------------------------------------------
            # NORMAL COMMAND COMPLETE
            # -------------------------------------------------

            if response_lower == "ok":

                return True

        raise RuntimeError(
            "Timeout waiting for GRBL response: "
            +
            command
        )


    # =====================================================
    # PROBE SURFACE
    # =====================================================

    def probe_surface(self):

        if self._stop_requested:

            return None

        command = (
            f"G38.2 "
            f"Z{self.z_min:.4f} "
            f"F{self.probe_feed:.3f}"
        )

        try:

            self.ser.write(
                (
                    command
                    +
                    "\n"
                ).encode()
            )

            self.ser.flush()

        except Exception as e:

            raise RuntimeError(
                f"Probe serial write error: {e}"
            )

        self.log_signal.emit(
            f">> {command}"
        )

        start_time = time.time()

        while (
            time.time()
            -
            start_time
            <
            120.0
        ):

            if self._stop_requested:

                return None

            try:

                if not self.ser.in_waiting:

                    time.sleep(
                        0.005
                    )

                    continue

                response = (
                    self.ser.readline()
                    .decode(
                        errors="ignore"
                    )
                    .strip()
                )

            except serial.SerialException as e:

                raise RuntimeError(
                    f"Probe serial read error: {e}"
                )

            if not response:

                continue

            self.log_signal.emit(
                f"<< {response}"
            )

            # =================================================
            # GRBL PROBE RESULT
            #
            # Standard:
            #
            # [PRB:X,Y,Z:1]
            #
            # Your controller:
            #
            # [PRB:X,Y,Z,A:1]
            #
            # Accept BOTH formats.
            # =================================================

            probe_match = re.search(
                r"\[PRB:"
                r"\s*"
                r"([-+]?(?:\d+(?:\.\d*)?|\.\d+))"
                r"\s*,"
                r"\s*"
                r"([-+]?(?:\d+(?:\.\d*)?|\.\d+))"
                r"\s*,"
                r"\s*"
                r"([-+]?(?:\d+(?:\.\d*)?|\.\d+))"
                r"(?:"
                r"\s*,"
                r"\s*"
                r"([-+]?(?:\d+(?:\.\d*)?|\.\d+))"
                r")?"
                r"\s*:"
                r"\s*"
                r"([01])"
                r"\]",
                response,
                re.IGNORECASE
            )

            if probe_match:

                prb_x = float(
                    probe_match.group(1)
                )

                prb_y = float(
                    probe_match.group(2)
                )

                prb_z = float(
                    probe_match.group(3)
                )

                # Optional fourth axis.
                # We do not use it for AutoLevel.
                prb_a = probe_match.group(4)

                if prb_a is not None:

                    prb_a = float(
                        prb_a
                    )

                success = int(
                    probe_match.group(5)
                )

                # -------------------------------------------------
                # Log exactly what GRBL reported.
                # -------------------------------------------------

                if prb_a is not None:

                    self.log_signal.emit(
                        "PROBE RESULT: "
                        f"X={prb_x:.4f} "
                        f"Y={prb_y:.4f} "
                        f"Z={prb_z:.4f} "
                        f"A={prb_a:.4f} "
                        f"CONTACT={success}"
                    )

                else:

                    self.log_signal.emit(
                        "PROBE RESULT: "
                        f"X={prb_x:.4f} "
                        f"Y={prb_y:.4f} "
                        f"Z={prb_z:.4f} "
                        f"CONTACT={success}"
                    )

                # -------------------------------------------------
                # Successful probe.
                # -------------------------------------------------

                if success == 1:

                    return (
                        prb_x,
                        prb_y,
                        prb_z,
                        success
                    )

                # -------------------------------------------------
                # Probe completed but did not contact.
                # -------------------------------------------------

                raise RuntimeError(
                    "GRBL probe completed without "
                    "detecting probe contact."
                )

            # =================================================
            # ALARM
            # =================================================

            if response.lower().startswith(
                "alarm"
            ):

                raise RuntimeError(
                    f"GRBL alarm during probe: "
                    f"{response}"
                )

            # =================================================
            # ERROR
            # =================================================

            if response.lower().startswith(
                "error"
            ):

                raise RuntimeError(
                    f"GRBL probe error: "
                    f"{response}"
                )

            # =================================================
            # OK
            #
            # We deliberately do NOT finish on "ok".
            #
            # The PRB line is what contains the actual probe
            # position. We wait for that line.
            # =================================================

            if response.lower() == "ok":

                continue

        raise RuntimeError(
            "Timeout waiting for GRBL probe result."
        )



    # =====================================================
    # RUN
    # =====================================================

    def run(self):

        try:

            if (
                not self.ser
                or
                not self.ser.is_open
            ):

                raise RuntimeError(
                    "Serial connection is not available."
                )

            x_values = self.build_axis(
                self.x_min,
                self.x_max
            )

            y_values = self.build_axis(
                self.y_min,
                self.y_max
            )

            if (
                not x_values
                or
                not y_values
            ):

                raise RuntimeError(
                    "Invalid AutoLevel scan area."
                )

            total = (
                len(x_values)
                *
                len(y_values)
            )

            self.log_signal.emit(
                "AUTOLEVEL SCAN STARTED"
            )

            self.status_signal.emit(
                "PREPARING GRBL..."
            )

            # =================================================
            # CLEAR OLD SERIAL DATA
            # =================================================

            try:

                self.ser.reset_input_buffer()

            except Exception:
                pass

            # =================================================
            # METRIC
            # =================================================

            self.send_and_wait(
                "G21"
            )

            # =================================================
            # ABSOLUTE POSITIONING
            # =================================================

            self.send_and_wait(
                "G90"
            )

            # =================================================
            # SAFE Z
            # =================================================

            self.send_and_wait(
                f"G0 Z{self.z_max:.4f}"
            )

            point_number = 0

            # =================================================
            # SERPENTINE GRID
            # =================================================

            for row_index, y in enumerate(
                y_values
            ):

                if self._stop_requested:

                    self.stopped_signal.emit()

                    return

                if row_index % 2 == 0:

                    row_x_values = x_values

                else:

                    row_x_values = list(
                        reversed(
                            x_values
                        )
                    )

                for x in row_x_values:

                    if self._stop_requested:

                        self.stopped_signal.emit()

                        return

                    point_number += 1

                    self.status_signal.emit(
                        f"PROBING "
                        f"{point_number}/{total}"
                    )

                    # =================================================
                    # CALCULATE ACTUAL PROBE POSITION
                    # =================================================

                    machine_x = (
                        x
                        -
                        self.probe_x_offset
                    )

                    machine_y = (
                        y
                        -
                        self.probe_y_offset
                    )

                    # =================================================
                    # SAFE Z
                    # =================================================

                    self.send_and_wait(
                        f"G0 Z{self.z_max:.4f}"
                    )

                    # =================================================
                    # MOVE TO XY
                    # =================================================

                    self.send_and_wait(
                        f"G0 "
                        f"X{machine_x:.4f} "
                        f"Y{machine_y:.4f}"
                    )

                    # =================================================
                    # PROBE
                    # =================================================

                    self.status_signal.emit(
                        f"PROBING "
                        f"{point_number}/{total}"
                    )

                    probe_result = (
                        self.probe_surface()
                    )

                    if probe_result is None:

                        if self._stop_requested:

                            self.stopped_signal.emit()

                            return

                        raise RuntimeError(
                            "Probe was stopped."
                        )

                    (
                        prb_x,
                        prb_y,
                        prb_z,
                        success
                    ) = probe_result

                    if success != 1:

                        raise RuntimeError(
                            "Probe contact was not detected."
                        )

                    # =================================================
                    # CALCULATE SURFACE Z
                    # =================================================

                    surface_z = (
                        prb_z
                        +
                        self.probe_z_offset
                    )

                    # =================================================
                    # STORE POINT
                    # =================================================

                    point = {
                        "x": float(x),
                        "y": float(y),
                        "z": float(surface_z)
                    }

                    self.points.append(
                        point
                    )

                    # =================================================
                    # SEND POINT TO GUI
                    # =================================================

                    self.point_signal.emit(
                        point_number,
                        total,
                        float(x),
                        float(y),
                        float(surface_z)
                    )

                    # =================================================
                    # UPDATE PROGRESS
                    # =================================================

                    progress = int(
                        (
                            point_number
                            /
                            max(total, 1)
                        )
                        *
                        100
                    )

                    self.progress_signal.emit(
                        progress
                    )

                    # =================================================
                    # RETRACT
                    # =================================================

                    if self.z_retract > 0:

                        self.send_and_wait(
                            "G91"
                        )

                        self.send_and_wait(
                            f"G0 Z{self.z_retract:.4f}"
                        )

                        self.send_and_wait(
                            "G90"
                        )

                    else:

                        self.send_and_wait(
                            f"G0 Z{self.z_max:.4f}"
                        )

            # =================================================
            # FINAL SAFE Z
            # =================================================

            self.send_and_wait(
                f"G0 Z{self.z_max:.4f}"
            )

            self.progress_signal.emit(
                100
            )

            self.status_signal.emit(
                "SCAN COMPLETE"
            )

            self.log_signal.emit(
                "AUTOLEVEL SURFACE MAP COMPLETE"
            )

            self.finished_signal.emit(
                self.points
            )

        except Exception as e:

            if self._stop_requested:

                self.stopped_signal.emit()

                return

            self.error_signal.emit(
                str(e)
            )


# =========================================================
# GCODE EDITOR
# =========================================================

class GCodeEditor(QtWidgets.QPlainTextEdit):

    line_clicked = QtCore.pyqtSignal(int)

    def __init__(self):

        super().__init__()

        self.setLineWrapMode(
            QtWidgets.QPlainTextEdit.NoWrap
        )

        self.setReadOnly(True)

        self.setFont(
            QtGui.QFont(
                "Consolas",
                9
            )
        )

        self.current_line = -1

    def highlight_line(self, line_number):

        self.current_line = line_number

        selection = QtWidgets.QTextEdit.ExtraSelection()

        selection.format.setBackground(
            QtGui.QColor("#f0a500")
        )

        selection.format.setForeground(
            QtGui.QColor("#111111")
        )

        selection.format.setProperty(
            QtGui.QTextFormat.FullWidthSelection,
            True
        )

        block = (
            self.document()
            .findBlockByNumber(
                line_number
            )
        )

        if block.isValid():

            selection.cursor = QtGui.QTextCursor(
                block
            )

            self.setExtraSelections(
                [selection]
            )

            self.setTextCursor(
                selection.cursor
            )

            self.ensureCursorVisible()

    def clear_highlight(self):

        self.current_line = -1

        self.setExtraSelections([])


# =========================================================
# MAIN WINDOW
# =========================================================

class CNCSender(QtWidgets.QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            f"{APP_NAME} {APP_VERSION}"
        )

        self.resize(
            1550,
            900
        )

        self.setMinimumSize(
            1100,
            700
        )

        self.ser = None
        self.sender = None
        self.autolevel_worker = None

        self.gcode_lines = []
        self.original_gcode_lines = []
        self.current_file = ""

        self.gcode_is_levelled = False

        self.autolevel_points = []

        self.job_start_time = None
        self.last_wco = None

        self.jog_buttons = []
        self.zero_buttons = []

        self.is_paused = False

        self.feed_override = 100
        self.spindle_override = 100

        self._build_ui()

        self.status_timer = QtCore.QTimer()

        self.status_timer.timeout.connect(
            self.poll_status
        )

        self.progress_timer = QtCore.QTimer()

        self.progress_timer.timeout.connect(
            self.update_progress_info
        )

        self.apply_styles()

        self.setAcceptDrops(True)

    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):

        central = QtWidgets.QWidget()

        self.setCentralWidget(
            central
        )

        main = QtWidgets.QVBoxLayout(
            central
        )

        main.setContentsMargins(
            8,
            8,
            8,
            4
        )

        main.setSpacing(7)

        # =====================================================
        # HEADER
        # =====================================================

        header = QtWidgets.QFrame()

        header.setObjectName(
            "Header"
        )

        header.setFixedHeight(72)

        header_layout = QtWidgets.QHBoxLayout(
            header
        )

        header_layout.setContentsMargins(
            12,
            5,
            15,
            5
        )

        logo = QtWidgets.QLabel()

        pixmap = QtGui.QPixmap(
            LOGO_PATH
        )

        if not pixmap.isNull():

            pixmap = pixmap.scaled(
                58,
                58,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )

            logo.setPixmap(
                pixmap
            )

        logo.setFixedWidth(70)

        logo.setAlignment(
            QtCore.Qt.AlignCenter
        )

        header_layout.addWidget(
            logo
        )

        brand_layout = QtWidgets.QVBoxLayout()

        brand = QtWidgets.QLabel(
            "MAD HAT"
        )

        brand.setObjectName(
            "Brand"
        )

        brand_sub = QtWidgets.QLabel(
            "CNC CONTROL SOFTWARE"
        )

        brand_sub.setObjectName(
            "BrandSub"
        )

        brand_layout.addWidget(
            brand
        )

        brand_layout.addWidget(
            brand_sub
        )

        header_layout.addLayout(
            brand_layout
        )

        header_layout.addStretch()

        self.header_status = QtWidgets.QLabel(
            "● DISCONNECTED"
        )

        self.header_status.setObjectName(
            "Status"
        )

        header_layout.addWidget(
            self.header_status
        )

        header_layout.addSpacing(20)

        version = QtWidgets.QLabel(
            APP_VERSION
        )

        version.setStyleSheet(
            "color:#777777;"
        )

        header_layout.addWidget(
            version
        )

        main.addWidget(
            header
        )

        # =====================================================
        # WORKSPACE
        # =====================================================

        workspace = QtWidgets.QHBoxLayout()

        workspace.setSpacing(7)

        main.addLayout(
            workspace,
            1
        )

        # =====================================================
        # LEFT SCROLL
        # =====================================================

        left_scroll = QtWidgets.QScrollArea()

        left_scroll.setFixedWidth(350)

        left_scroll.setWidgetResizable(True)

        left_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )

        left_scroll.setFrameShape(
            QtWidgets.QFrame.NoFrame
        )

        left_container = QtWidgets.QWidget()

        left_scroll.setWidget(
            left_container
        )

        left = QtWidgets.QVBoxLayout(
            left_container
        )

        left.setContentsMargins(
            0,
            0,
            2,
            0
        )

        left.setSpacing(7)

        workspace.addWidget(
            left_scroll
        )

        # =====================================================
        # CONNECTION
        # =====================================================

        connection = self.make_card()

        c = QtWidgets.QVBoxLayout(
            connection
        )

        c.addWidget(
            self.section_title(
                "CONNECTION"
            )
        )

        port_row = QtWidgets.QHBoxLayout()

        self.port_box = QtWidgets.QComboBox()

        self.refresh_ports()

        self.refresh_btn = QtWidgets.QPushButton(
            "⟳"
        )

        self.refresh_btn.setFixedWidth(
            40
        )

        port_row.addWidget(
            self.port_box,
            1
        )

        port_row.addWidget(
            self.refresh_btn
        )

        c.addLayout(
            port_row
        )

        baud_row = QtWidgets.QHBoxLayout()

        baud_row.addWidget(
            self.small_label(
                "BAUD"
            )
        )

        self.baud_box = QtWidgets.QComboBox()

        self.baud_box.addItems(
            BAUD_RATES
        )

        self.baud_box.setCurrentText(
            "115200"
        )

        baud_row.addWidget(
            self.baud_box
        )

        c.addLayout(
            baud_row
        )

        conn_buttons = QtWidgets.QHBoxLayout()

        self.connect_btn = QtWidgets.QPushButton(
            "CONNECT"
        )

        self.disconnect_btn = QtWidgets.QPushButton(
            "DISCONNECT"
        )

        self.disconnect_btn.setEnabled(
            False
        )

        conn_buttons.addWidget(
            self.connect_btn
        )

        conn_buttons.addWidget(
            self.disconnect_btn
        )

        c.addLayout(
            conn_buttons
        )

        self.refresh_btn.clicked.connect(
            self.refresh_ports
        )

        self.connect_btn.clicked.connect(
            self.connect
        )

        self.disconnect_btn.clicked.connect(
            self.disconnect
        )

        left.addWidget(
            connection
        )

        # =====================================================
        # JOB FILE
        # =====================================================

        file_card = self.make_card()

        f = QtWidgets.QVBoxLayout(
            file_card
        )

        f.addWidget(
            self.section_title(
                "JOB FILE"
            )
        )

        file_buttons = QtWidgets.QHBoxLayout()

        self.load_btn = QtWidgets.QPushButton(
            "LOAD G-CODE"
        )

        self.clear_btn = QtWidgets.QPushButton(
            "CLEAR"
        )

        file_buttons.addWidget(
            self.load_btn,
            1
        )

        file_buttons.addWidget(
            self.clear_btn
        )

        f.addLayout(
            file_buttons
        )

        self.file_label = QtWidgets.QLabel(
            "No file loaded"
        )

        self.file_label.setWordWrap(
            True
        )

        self.file_label.setObjectName(
            "SmallLabel"
        )

        f.addWidget(
            self.file_label
        )

        self.load_btn.clicked.connect(
            self.load_gcode
        )

        self.clear_btn.clicked.connect(
            self.clear_gcode
        )

        left.addWidget(
            file_card
        )

        # =====================================================
        # JOB CONTROL
        # =====================================================

        job_card = self.make_card()

        j = QtWidgets.QVBoxLayout(
            job_card
        )

        j.addWidget(
            self.section_title(
                "JOB CONTROL"
            )
        )

        row1 = QtWidgets.QHBoxLayout()

        self.play_btn = QtWidgets.QPushButton(
            "▶ PLAY"
        )

        self.play_btn.setObjectName(
            "Play"
        )

        self.pause_btn = QtWidgets.QPushButton(
            "Ⅱ PAUSE"
        )

        self.pause_btn.setObjectName(
            "Pause"
        )

        self.stop_btn = QtWidgets.QPushButton(
            "■ STOP"
        )

        self.stop_btn.setObjectName(
            "Stop"
        )

        row1.addWidget(
            self.play_btn
        )

        row1.addWidget(
            self.pause_btn
        )

        row1.addWidget(
            self.stop_btn
        )

        j.addLayout(
            row1
        )

        row2 = QtWidgets.QHBoxLayout()

        self.resume_btn = QtWidgets.QPushButton(
            "▶ RESUME"
        )

        self.resume_btn.setEnabled(
            False
        )

        self.check_btn = QtWidgets.QPushButton(
            "CHECK"
        )

        row2.addWidget(
            self.resume_btn
        )

        row2.addWidget(
            self.check_btn
        )

        j.addLayout(
            row2
        )

        self.progress_bar = QtWidgets.QProgressBar()

        j.addWidget(
            self.progress_bar
        )

        time_row = QtWidgets.QHBoxLayout()

        self.run_time_label = QtWidgets.QLabel(
            "RUN 00:00:00"
        )

        self.eta_label = QtWidgets.QLabel(
            "ETA --:--:--"
        )

        time_row.addWidget(
            self.run_time_label
        )

        time_row.addStretch()

        time_row.addWidget(
            self.eta_label
        )

        j.addLayout(
            time_row
        )

        self.play_btn.clicked.connect(
            self.play
        )

        self.pause_btn.clicked.connect(
            self.pause_job
        )

        self.resume_btn.clicked.connect(
            self.resume_job
        )

        self.stop_btn.clicked.connect(
            self.stop
        )

        self.check_btn.clicked.connect(
            self.check_gcode
        )

        left.addWidget(
            job_card
        )

        # =====================================================
        # MACHINE COMMANDS
        # =====================================================

        machine_card = self.make_card()

        mc = QtWidgets.QVBoxLayout(
            machine_card
        )

        mc.addWidget(
            self.section_title(
                "MACHINE CONTROL"
            )
        )

        machine_grid = QtWidgets.QGridLayout()

        self.home_btn = QtWidgets.QPushButton(
            "$H  HOME"
        )

        self.home_btn.setObjectName(
            "Home"
        )

        self.unlock_btn = QtWidgets.QPushButton(
            "$X  UNLOCK"
        )

        self.reset_btn = QtWidgets.QPushButton(
            "SOFT RESET"
        )

        self.reset_btn.setObjectName(
            "Danger"
        )

        self.zero_all_btn = QtWidgets.QPushButton(
            "ZERO ALL"
        )

        self.go_zero_btn = QtWidgets.QPushButton(
            "GO TO ZERO"
        )

        machine_grid.addWidget(
            self.home_btn,
            0,
            0
        )

        machine_grid.addWidget(
            self.unlock_btn,
            0,
            1
        )

        machine_grid.addWidget(
            self.zero_all_btn,
            1,
            0
        )

        machine_grid.addWidget(
            self.go_zero_btn,
            1,
            1
        )

        machine_grid.addWidget(
            self.reset_btn,
            2,
            0,
            1,
            2
        )

        mc.addLayout(
            machine_grid
        )

        self.home_btn.clicked.connect(
            self.home_machine
        )

        self.unlock_btn.clicked.connect(
            lambda:
            self.send_command("$X")
        )

        self.reset_btn.clicked.connect(
            self.soft_reset
        )

        self.zero_all_btn.clicked.connect(
            self.zero_all
        )

        self.go_zero_btn.clicked.connect(
            self.go_zero
        )

        self.zero_buttons.extend(
            [
                self.home_btn,
                self.unlock_btn,
                self.reset_btn,
                self.zero_all_btn,
                self.go_zero_btn
            ]
        )

        left.addWidget(
            machine_card
        )

        # =====================================================
        # JOG
        # =====================================================

        jog_card = self.make_card()

        g = QtWidgets.QVBoxLayout(
            jog_card
        )

        g.addWidget(
            self.section_title(
                "JOG CONTROL"
            )
        )

        distance_row = QtWidgets.QHBoxLayout()

        distance_row.addWidget(
            self.small_label(
                "STEP"
            )
        )

        self.jog_distance_box = QtWidgets.QComboBox()

        self.jog_distance_box.addItems(
            [
                "0.1",
                "0.5",
                "1",
                "5",
                "10",
                "25",
                "50",
                "100"
            ]
        )

        self.jog_distance_box.setCurrentText(
            "1"
        )

        distance_row.addWidget(
            self.jog_distance_box
        )

        distance_row.addWidget(
            self.small_label(
                "mm"
            )
        )

        g.addLayout(
            distance_row
        )

        speed_row = QtWidgets.QHBoxLayout()

        speed_row.addWidget(
            self.small_label(
                "FEED"
            )
        )

        self.jog_speed_box = QtWidgets.QSpinBox()

        self.jog_speed_box.setRange(
            1,
            30000
        )

        self.jog_speed_box.setValue(
            1000
        )

        speed_row.addWidget(
            self.jog_speed_box
        )

        speed_row.addWidget(
            self.small_label(
                "mm/min"
            )
        )

        g.addLayout(
            speed_row
        )

        jog_grid = QtWidgets.QGridLayout()

        jog_grid.addWidget(
            self.make_jog("Y+"),
            0,
            1
        )

        jog_grid.addWidget(
            self.make_jog("X-"),
            1,
            0
        )

        jog_grid.addWidget(
            self.make_jog("X+"),
            1,
            2
        )

        jog_grid.addWidget(
            self.make_jog("Y-"),
            2,
            1
        )

        jog_grid.addWidget(
            self.make_jog("Z+"),
            3,
            0
        )

        jog_grid.addWidget(
            self.make_jog("Z-"),
            3,
            2
        )

        g.addLayout(
            jog_grid
        )

        left.addWidget(
            jog_card
        )

        # =====================================================
        # ZERO AXES
        # =====================================================

        zero_card = self.make_card()

        z = QtWidgets.QVBoxLayout(
            zero_card
        )

        z.addWidget(
            self.section_title(
                "WORK ZERO"
            )
        )

        zero_grid = QtWidgets.QGridLayout()

        for column, axis in enumerate(
            ["X", "Y", "Z"]
        ):

            btn = QtWidgets.QPushButton(
                f"{axis} ZERO"
            )

            btn.setObjectName(
                "Zero"
            )

            btn.clicked.connect(
                lambda checked=False,
                a=axis:
                self.zero_axis(a)
            )

            self.zero_buttons.append(
                btn
            )

            zero_grid.addWidget(
                btn,
                0,
                column
            )

        z.addLayout(
            zero_grid
        )

        left.addWidget(
            zero_card
        )

        # =====================================================
        # SPINDLE
        # =====================================================

        spindle_card = self.make_card()

        sp = QtWidgets.QVBoxLayout(
            spindle_card
        )

        sp.addWidget(
            self.section_title(
                "SPINDLE"
            )
        )

        rpm_row = QtWidgets.QHBoxLayout()

        rpm_row.addWidget(
            self.small_label(
                "RPM"
            )
        )

        self.rpm_box = QtWidgets.QSpinBox()

        self.rpm_box.setRange(
            0,
            100000
        )

        self.rpm_box.setValue(
            10000
        )

        rpm_row.addWidget(
            self.rpm_box
        )

        sp.addLayout(
            rpm_row
        )

        spindle_buttons = QtWidgets.QGridLayout()

        self.spindle_cw_btn = QtWidgets.QPushButton(
            "M3  CW"
        )

        self.spindle_ccw_btn = QtWidgets.QPushButton(
            "M4  CCW"
        )

        self.spindle_off_btn = QtWidgets.QPushButton(
            "M5  OFF"
        )

        spindle_buttons.addWidget(
            self.spindle_cw_btn,
            0,
            0
        )

        spindle_buttons.addWidget(
            self.spindle_ccw_btn,
            0,
            1
        )

        spindle_buttons.addWidget(
            self.spindle_off_btn,
            1,
            0,
            1,
            2
        )

        sp.addLayout(
            spindle_buttons
        )

        self.spindle_cw_btn.clicked.connect(
            self.spindle_cw
        )

        self.spindle_ccw_btn.clicked.connect(
            self.spindle_ccw
        )

        self.spindle_off_btn.clicked.connect(
            lambda:
            self.send_command("M5")
        )

        left.addWidget(
            spindle_card
        )

        # =====================================================
        # COOLANT
        # =====================================================

        coolant_card = self.make_card()

        co = QtWidgets.QVBoxLayout(
            coolant_card
        )

        co.addWidget(
            self.section_title(
                "COOLANT"
            )
        )

        coolant_grid = QtWidgets.QGridLayout()

        flood = QtWidgets.QPushButton(
            "M8 FLOOD"
        )

        mist = QtWidgets.QPushButton(
            "M7 MIST"
        )

        off = QtWidgets.QPushButton(
            "M9 OFF"
        )

        coolant_grid.addWidget(
            flood,
            0,
            0
        )

        coolant_grid.addWidget(
            mist,
            0,
            1
        )

        coolant_grid.addWidget(
            off,
            1,
            0,
            1,
            2
        )

        co.addLayout(
            coolant_grid
        )

        flood.clicked.connect(
            lambda:
            self.send_command("M8")
        )

        mist.clicked.connect(
            lambda:
            self.send_command("M7")
        )

        off.clicked.connect(
            lambda:
            self.send_command("M9")
        )

        left.addWidget(
            coolant_card
        )

        # =====================================================
        # OVERRIDES
        # =====================================================

        override_card = self.make_card()

        ov = QtWidgets.QVBoxLayout(
            override_card
        )

        ov.addWidget(
            self.section_title(
                "REALTIME OVERRIDES"
            )
        )

        feed_title = QtWidgets.QHBoxLayout()

        feed_title.addWidget(
            self.small_label(
                "FEED OVERRIDE"
            )
        )

        self.feed_override_label = QtWidgets.QLabel(
            "100%"
        )

        self.feed_override_label.setObjectName(
            "Value"
        )

        feed_title.addStretch()

        feed_title.addWidget(
            self.feed_override_label
        )

        ov.addLayout(
            feed_title
        )

        feed_buttons = QtWidgets.QHBoxLayout()

        feed_minus = QtWidgets.QPushButton(
            "-10%"
        )

        feed_reset = QtWidgets.QPushButton(
            "100%"
        )

        feed_plus = QtWidgets.QPushButton(
            "+10%"
        )

        feed_buttons.addWidget(
            feed_minus
        )

        feed_buttons.addWidget(
            feed_reset
        )

        feed_buttons.addWidget(
            feed_plus
        )

        ov.addLayout(
            feed_buttons
        )

        feed_minus.clicked.connect(
            lambda:
            self.feed_override_change(-10)
        )

        feed_reset.clicked.connect(
            lambda:
            self.feed_override_set(100)
        )

        feed_plus.clicked.connect(
            lambda:
            self.feed_override_change(10)
        )

        spindle_title = QtWidgets.QHBoxLayout()

        spindle_title.addWidget(
            self.small_label(
                "SPINDLE OVERRIDE"
            )
        )

        self.spindle_override_label = QtWidgets.QLabel(
            "100%"
        )

        self.spindle_override_label.setObjectName(
            "Value"
        )

        spindle_title.addStretch()

        spindle_title.addWidget(
            self.spindle_override_label
        )

        ov.addLayout(
            spindle_title
        )

        spindle_buttons = QtWidgets.QHBoxLayout()

        sm = QtWidgets.QPushButton(
            "-10%"
        )

        sr = QtWidgets.QPushButton(
            "100%"
        )

        sx = QtWidgets.QPushButton(
            "+10%"
        )

        spindle_buttons.addWidget(
            sm
        )

        spindle_buttons.addWidget(
            sr
        )

        spindle_buttons.addWidget(
            sx
        )

        ov.addLayout(
            spindle_buttons
        )

        sm.clicked.connect(
            lambda:
            self.spindle_override_change(-10)
        )

        sr.clicked.connect(
            lambda:
            self.spindle_override_set(100)
        )

        sx.clicked.connect(
            lambda:
            self.spindle_override_change(10)
        )

        left.addWidget(
            override_card
        )

        left.addStretch()

        # =====================================================
        # RIGHT SIDE
        # =====================================================

        right = QtWidgets.QVBoxLayout()

        right.setSpacing(
            7
        )

        workspace.addLayout(
            right,
            1
        )

        # =====================================================
        # DRO
        # =====================================================

        dro_card = self.make_card()

        dro_layout = QtWidgets.QHBoxLayout(
            dro_card
        )

        state_box = QtWidgets.QVBoxLayout()

        state_box.addWidget(
            self.section_title(
                "MACHINE"
            )
        )

        self.state_label = QtWidgets.QLabel(
            "DISCONNECTED"
        )

        self.state_label.setObjectName(
            "Status"
        )

        state_box.addWidget(
            self.state_label
        )

        dro_layout.addLayout(
            state_box
        )

        dro_layout.addStretch()

        self.dro_x = self.make_dro("X")
        self.dro_y = self.make_dro("Y")
        self.dro_z = self.make_dro("Z")

        dro_layout.addLayout(
            self.dro_x
        )

        dro_layout.addLayout(
            self.dro_y
        )

        dro_layout.addLayout(
            self.dro_z
        )

        fs = QtWidgets.QVBoxLayout()

        fs.addWidget(
            self.section_title(
                "LIVE"
            )
        )

        self.feed_label = QtWidgets.QLabel(
            "F 0"
        )

        self.feed_label.setObjectName(
            "Value"
        )

        self.speed_label = QtWidgets.QLabel(
            "S 0"
        )

        self.speed_label.setObjectName(
            "Value"
        )

        fs.addWidget(
            self.feed_label
        )

        fs.addWidget(
            self.speed_label
        )

        dro_layout.addSpacing(
            15
        )

        dro_layout.addLayout(
            fs
        )

        right.addWidget(
            dro_card
        )

        # =====================================================
        # TABS
        # =====================================================

        tabs = QtWidgets.QTabWidget()

        # =====================================================
        # 3D TOOLPATH TAB
        # =====================================================

        visual_page = QtWidgets.QWidget()

        vp = QtWidgets.QVBoxLayout(
            visual_page
        )

        visual_header = QtWidgets.QHBoxLayout()

        visual_header.addWidget(
            self.section_title(
                "3D TOOLPATH VISUALISER"
            )
        )

        visual_header.addStretch()

        self.view_top_btn = QtWidgets.QPushButton(
            "TOP"
        )

        self.view_front_btn = QtWidgets.QPushButton(
            "FRONT"
        )

        self.view_right_btn = QtWidgets.QPushButton(
            "RIGHT"
        )

        self.view_iso_btn = QtWidgets.QPushButton(
            "ISO"
        )

        self.fit_btn = QtWidgets.QPushButton(
            "FIT"
        )

        self.clear_view_btn = QtWidgets.QPushButton(
            "CLEAR"
        )

        self.view_top_btn.setFixedWidth(
            60
        )

        self.view_front_btn.setFixedWidth(
            65
        )

        self.view_right_btn.setFixedWidth(
            65
        )

        self.view_iso_btn.setFixedWidth(
            60
        )

        self.fit_btn.setFixedWidth(
            55
        )

        self.clear_view_btn.setFixedWidth(
            65
        )

        visual_header.addWidget(
            self.view_top_btn
        )

        visual_header.addWidget(
            self.view_front_btn
        )

        visual_header.addWidget(
            self.view_right_btn
        )

        visual_header.addWidget(
            self.view_iso_btn
        )

        visual_header.addWidget(
            self.fit_btn
        )

        visual_header.addWidget(
            self.clear_view_btn
        )

        vp.addLayout(
            visual_header
        )

        self.plot = gl.GLViewWidget()

        self.plot.setBackgroundColor(
            (8, 8, 8)
        )

        self.plot.setCameraPosition(
            distance=200,
            elevation=30,
            azimuth=-45
        )

        vp.addWidget(
            self.plot,
            1
        )

        self.grid = gl.GLGridItem()

        self.grid.setSize(
            200,
            200
        )

        self.grid.setSpacing(
            10,
            10
        )

        self.plot.addItem(
            self.grid
        )

        self.axis_x = gl.GLLinePlotItem(
            pos=np.array(
                [
                    [0, 0, 0],
                    [100, 0, 0]
                ],
                dtype=float
            ),
            color=(1.0, 0.25, 0.15, 1.0),
            width=2,
            antialias=True,
            mode="lines"
        )

        self.axis_y = gl.GLLinePlotItem(
            pos=np.array(
                [
                    [0, 0, 0],
                    [0, 100, 0]
                ],
                dtype=float
            ),
            color=(0.25, 1.0, 0.25, 1.0),
            width=2,
            antialias=True,
            mode="lines"
        )

        self.axis_z = gl.GLLinePlotItem(
            pos=np.array(
                [
                    [0, 0, 0],
                    [0, 0, 100]
                ],
                dtype=float
            ),
            color=(0.25, 0.55, 1.0, 1.0),
            width=2,
            antialias=True,
            mode="lines"
        )

        self.plot.addItem(
            self.axis_x
        )

        self.plot.addItem(
            self.axis_y
        )

        self.plot.addItem(
            self.axis_z
        )

        self.cut_3d = gl.GLLinePlotItem(
            color=(0.0, 1.0, 1.0, 1.0),
            width=2,
            antialias=True,
            mode="lines"
        )

        self.rapid_3d = gl.GLLinePlotItem(
            color=(1.0, 0.0, 0.0, 1.0),
            width=1,
            antialias=True,
            mode="lines"
        )

        self.plot.addItem(
            self.rapid_3d
        )

        self.plot.addItem(
            self.cut_3d
        )

        self.tool_3d = gl.GLScatterPlotItem(
            pos=np.array(
                [[0, 0, 0]],
                dtype=float
            ),
            size=12,
            color=(1.0, 0.15, 0.15, 1.0),
            pxMode=True
        )

        self.plot.addItem(
            self.tool_3d
        )

        self.cut_points_3d = np.empty(
            (0, 3),
            dtype=float
        )

        self.rapid_points_3d = np.empty(
            (0, 3),
            dtype=float
        )

        self.fit_btn.clicked.connect(
            self.fit_visualiser
        )

        self.clear_view_btn.clicked.connect(
            self.clear_visualiser
        )

        self.view_top_btn.clicked.connect(
            self.view_top
        )

        self.view_front_btn.clicked.connect(
            self.view_front
        )

        self.view_right_btn.clicked.connect(
            self.view_right
        )

        self.view_iso_btn.clicked.connect(
            self.view_iso
        )

        tabs.addTab(
            visual_page,
            "3D TOOLPATH"
        )


        # =====================================================
        # AUTOLEVEL TAB
        # =====================================================

        autolevel_page = QtWidgets.QWidget()

        # -----------------------------------------------------
        # AUTOLEVEL PAGE SCROLL AREA
        # -----------------------------------------------------

        autolevel_scroll = QtWidgets.QScrollArea()

        autolevel_scroll.setWidgetResizable(
            True
        )

        autolevel_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )

        autolevel_scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAsNeeded
        )

        autolevel_scroll.setFrameShape(
            QtWidgets.QFrame.NoFrame
        )

        # -----------------------------------------------------
        # AUTOLEVEL SCROLL CONTENT
        # -----------------------------------------------------

        autolevel_content = QtWidgets.QWidget()

        al_main = QtWidgets.QVBoxLayout(
            autolevel_content
        )

        al_main.setContentsMargins(
            15,
            15,
            15,
            20
        )

        al_main.setSpacing(
            18
        )

        # -----------------------------------------------------
        # AUTOLEVEL HEADER
        # -----------------------------------------------------

        al_header = QtWidgets.QHBoxLayout()

        al_header.setContentsMargins(
            5,
            5,
            5,
            5
        )

        al_header.setSpacing(
            15
        )

        al_header.addWidget(
            self.section_title(
                "AUTOLEVEL / SURFACE PROBING"
            )
        )

        al_header.addStretch()

        self.autolevel_status_label = QtWidgets.QLabel(
            "NO SURFACE MAP"
        )

        self.autolevel_status_label.setObjectName(
            "Value"
        )

        al_header.addWidget(
            self.autolevel_status_label
        )

        al_main.addLayout(
            al_header
        )

        # -----------------------------------------------------
        # SETTINGS
        # -----------------------------------------------------

        settings_layout = QtWidgets.QHBoxLayout()

        settings_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        settings_layout.setSpacing(
            20
        )

        # -----------------------------------------------------
        # SCAN AREA
        # -----------------------------------------------------

        area_group = QtWidgets.QGroupBox(
            "SCAN AREA"
        )

        area_group.setMinimumHeight(
            350
        )

        area_grid = QtWidgets.QGridLayout(
            area_group
        )

        area_grid.setContentsMargins(
            18,
            18,
            18,
            18
        )

        area_grid.setHorizontalSpacing(
            18
        )

        area_grid.setVerticalSpacing(
            16
        )

        self.al_x_min = self.make_double(
            -50.0,
            -100000.0,
            100000.0,
            3
        )

        self.al_x_max = self.make_double(
            50.0,
            -100000.0,
            100000.0,
            3
        )

        self.al_y_min = self.make_double(
            -50.0,
            -100000.0,
            100000.0,
            3
        )

        self.al_y_max = self.make_double(
            50.0,
            -100000.0,
            100000.0,
            3
        )

        self.al_z_min = self.make_double(
            -5.0,
            -100000.0,
            100000.0,
            3
        )

        self.al_z_max = self.make_double(
            5.0,
            -100000.0,
            100000.0,
            3
        )

        self.al_resolution = self.make_double(
            10.0,
            0.1,
            1000.0,
            2
        )

        # X MIN

        area_grid.addWidget(
            self.small_label("X MIN"),
            0,
            0
        )

        area_grid.addWidget(
            self.al_x_min,
            0,
            1
        )

        area_grid.addWidget(
            self.small_label("mm"),
            0,
            2
        )

        # X MAX

        area_grid.addWidget(
            self.small_label("X MAX"),
            1,
            0
        )

        area_grid.addWidget(
            self.al_x_max,
            1,
            1
        )

        area_grid.addWidget(
            self.small_label("mm"),
            1,
            2
        )

        # Y MIN

        area_grid.addWidget(
            self.small_label("Y MIN"),
            2,
            0
        )

        area_grid.addWidget(
            self.al_y_min,
            2,
            1
        )

        area_grid.addWidget(
            self.small_label("mm"),
            2,
            2
        )

        # Y MAX

        area_grid.addWidget(
            self.small_label("Y MAX"),
            3,
            0
        )

        area_grid.addWidget(
            self.al_y_max,
            3,
            1
        )

        area_grid.addWidget(
            self.small_label("mm"),
            3,
            2
        )

        # Z MIN

        area_grid.addWidget(
            self.small_label("Z MIN"),
            4,
            0
        )

        area_grid.addWidget(
            self.al_z_min,
            4,
            1
        )

        area_grid.addWidget(
            self.small_label("mm"),
            4,
            2
        )

        # Z MAX

        area_grid.addWidget(
            self.small_label("Z MAX"),
            5,
            0
        )

        area_grid.addWidget(
            self.al_z_max,
            5,
            1
        )

        area_grid.addWidget(
            self.small_label("mm"),
            5,
            2
        )

        # RESOLUTION

        area_grid.addWidget(
            self.small_label("RESOLUTION"),
            6,
            0
        )

        area_grid.addWidget(
            self.al_resolution,
            6,
            1
        )

        area_grid.addWidget(
            self.small_label("mm"),
            6,
            2
        )

        area_grid.setRowStretch(
            7,
            1
        )

        # -----------------------------------------------------
        # SCAN AREA SCROLL
        # -----------------------------------------------------

        area_scroll = QtWidgets.QScrollArea()

        area_scroll.setWidgetResizable(
            True
        )

        area_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )

        area_scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAsNeeded
        )

        area_scroll.setFrameShape(
            QtWidgets.QFrame.NoFrame
        )

        area_scroll.setMinimumHeight(
            350
        )

        area_scroll.setWidget(
            area_group
        )

        settings_layout.addWidget(
            area_scroll,
            1
        )

        # -----------------------------------------------------
        # PROBE SETTINGS
        # -----------------------------------------------------

        probe_group = QtWidgets.QGroupBox(
            "PROBE SETTINGS"
        )

        probe_group.setMinimumHeight(
            350
        )

        probe_grid = QtWidgets.QGridLayout(
            probe_group
        )

        probe_grid.setContentsMargins(
            18,
            18,
            18,
            18
        )

        probe_grid.setHorizontalSpacing(
            18
        )

        probe_grid.setVerticalSpacing(
            16
        )

        self.al_probe_feed = self.make_double(
            100.0,
            0.1,
            30000.0,
            1
        )

        self.al_z_retract = self.make_double(
            2.0,
            0.0,
            1000.0,
            3
        )

        self.al_z_surface = self.make_double(
            0.0,
            -100000.0,
            100000.0,
            3
        )

        self.al_probe_x_offset = self.make_double(
            0.0,
            -1000.0,
            1000.0,
            3
        )

        self.al_probe_y_offset = self.make_double(
            0.0,
            -1000.0,
            1000.0,
            3
        )

        self.al_probe_z_offset = self.make_double(
            0.0,
            -1000.0,
            1000.0,
            3
        )

        # PROBE FEED

        probe_grid.addWidget(
            self.small_label("PROBE FEED"),
            0,
            0
        )

        probe_grid.addWidget(
            self.al_probe_feed,
            0,
            1
        )

        probe_grid.addWidget(
            self.small_label("mm/min"),
            0,
            2
        )

        # Z RETRACT

        probe_grid.addWidget(
            self.small_label("Z RETRACT"),
            1,
            0
        )

        probe_grid.addWidget(
            self.al_z_retract,
            1,
            1
        )

        probe_grid.addWidget(
            self.small_label("mm"),
            1,
            2
        )

        # G-CODE Z SURFACE

        probe_grid.addWidget(
            self.small_label("G-CODE Z SURFACE"),
            2,
            0
        )

        probe_grid.addWidget(
            self.al_z_surface,
            2,
            1
        )

        probe_grid.addWidget(
            self.small_label("mm"),
            2,
            2
        )

        # PROBE X OFFSET

        probe_grid.addWidget(
            self.small_label("PROBE X OFFSET"),
            3,
            0
        )

        probe_grid.addWidget(
            self.al_probe_x_offset,
            3,
            1
        )

        probe_grid.addWidget(
            self.small_label("mm"),
            3,
            2
        )

        # PROBE Y OFFSET

        probe_grid.addWidget(
            self.small_label("PROBE Y OFFSET"),
            4,
            0
        )

        probe_grid.addWidget(
            self.al_probe_y_offset,
            4,
            1
        )

        probe_grid.addWidget(
            self.small_label("mm"),
            4,
            2
        )

        # PROBE Z OFFSET

        probe_grid.addWidget(
            self.small_label("PROBE Z OFFSET"),
            5,
            0
        )

        probe_grid.addWidget(
            self.al_probe_z_offset,
            5,
            1
        )

        probe_grid.addWidget(
            self.small_label("mm"),
            5,
            2
        )

        probe_grid.setRowStretch(
            6,
            1
        )

        # -----------------------------------------------------
        # PROBE SETTINGS SCROLL
        # -----------------------------------------------------

        probe_scroll = QtWidgets.QScrollArea()

        probe_scroll.setWidgetResizable(
            True
        )

        probe_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )

        probe_scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAsNeeded
        )

        probe_scroll.setFrameShape(
            QtWidgets.QFrame.NoFrame
        )

        probe_scroll.setMinimumHeight(
            350
        )

        probe_scroll.setWidget(
            probe_group
        )

        settings_layout.addWidget(
            probe_scroll,
            1
        )

        al_main.addLayout(
            settings_layout
        )

        # -----------------------------------------------------
        # CONTROLS
        # -----------------------------------------------------

        controls_card = self.make_card()

        controls_layout = QtWidgets.QVBoxLayout(
            controls_card
        )

        controls_layout.setContentsMargins(
            18,
            18,
            18,
            18
        )

        controls_layout.setSpacing(
            14
        )

        controls_title = QtWidgets.QHBoxLayout()

        controls_title.setSpacing(
            15
        )

        controls_title.addWidget(
            self.section_title(
                "AUTOLEVEL CONTROL"
            )
        )

        controls_title.addStretch()

        self.al_point_label = QtWidgets.QLabel(
            "POINT 0 / 0"
        )

        self.al_point_label.setObjectName(
            "Value"
        )

        controls_title.addWidget(
            self.al_point_label
        )

        controls_layout.addLayout(
            controls_title
        )

        self.al_progress = QtWidgets.QProgressBar()

        self.al_progress.setMinimumHeight(
            22
        )

        controls_layout.addWidget(
            self.al_progress
        )

        # -----------------------------------------------------
        # CONTROL BUTTON ROW 1
        # -----------------------------------------------------

        button_row1 = QtWidgets.QHBoxLayout()

        button_row1.setSpacing(
            12
        )

        self.al_scan_btn = QtWidgets.QPushButton(
            "SCAN SURFACE"
        )

        self.al_stop_btn = QtWidgets.QPushButton(
            "STOP SCAN"
        )

        self.al_clear_btn = QtWidgets.QPushButton(
            "CLEAR SCAN"
        )

        button_row1.addWidget(
            self.al_scan_btn
        )

        button_row1.addWidget(
            self.al_stop_btn
        )

        button_row1.addWidget(
            self.al_clear_btn
        )

        controls_layout.addLayout(
            button_row1
        )

        # -----------------------------------------------------
        # CONTROL BUTTON ROW 2
        # -----------------------------------------------------

        button_row2 = QtWidgets.QHBoxLayout()

        button_row2.setSpacing(
            12
        )

        self.al_save_btn = QtWidgets.QPushButton(
            "SAVE SCAN"
        )

        self.al_load_btn = QtWidgets.QPushButton(
            "LOAD SCAN"
        )

        self.al_apply_btn = QtWidgets.QPushButton(
            "APPLY TO G-CODE"
        )

        self.al_restore_btn = QtWidgets.QPushButton(
            "RESTORE ORIGINAL"
        )

        self.al_export_btn = QtWidgets.QPushButton(
            "EXPORT LEVELLED G-CODE"
        )

        button_row2.addWidget(
            self.al_save_btn
        )

        button_row2.addWidget(
            self.al_load_btn
        )

        button_row2.addWidget(
            self.al_apply_btn
        )

        button_row2.addWidget(
            self.al_restore_btn
        )

        button_row2.addWidget(
            self.al_export_btn
        )

        controls_layout.addLayout(
            button_row2
        )

        # -----------------------------------------------------
        # BUTTON CONNECTIONS
        # -----------------------------------------------------

        self.al_scan_btn.clicked.connect(
            self.start_autolevel
        )

        self.al_stop_btn.clicked.connect(
            self.stop_autolevel
        )

        self.al_clear_btn.clicked.connect(
            self.clear_autolevel
        )

        self.al_save_btn.clicked.connect(
            self.save_autolevel
        )

        self.al_load_btn.clicked.connect(
            self.load_autolevel
        )

        self.al_apply_btn.clicked.connect(
            self.apply_autolevel_to_gcode
        )

        self.al_restore_btn.clicked.connect(
            self.restore_original_gcode
        )

        self.al_export_btn.clicked.connect(
            self.export_levelled_gcode
        )

        al_main.addWidget(
            controls_card
        )

        # -----------------------------------------------------
        # CURRENT POINT
        # -----------------------------------------------------

        point_card = self.make_card()

        point_card.setMinimumHeight(
            80
        )

        point_layout = QtWidgets.QHBoxLayout(
            point_card
        )

        point_layout.setContentsMargins(
            18,
            15,
            18,
            15
        )

        point_layout.setSpacing(
            20
        )

        self.al_current_x = self.make_value_label(
            "X 0.000"
        )

        self.al_current_y = self.make_value_label(
            "Y 0.000"
        )

        self.al_current_z = self.make_value_label(
            "Z 0.000"
        )

        point_layout.addWidget(
            self.al_current_x
        )

        point_layout.addWidget(
            self.al_current_y
        )

        point_layout.addWidget(
            self.al_current_z
        )

        al_main.addWidget(
            point_card
        )

        # -----------------------------------------------------
        # PROBE MAP
        # -----------------------------------------------------

        table_card = self.make_card()

        table_card.setMinimumHeight(
            300
        )

        table_layout = QtWidgets.QVBoxLayout(
            table_card
        )

        table_layout.setContentsMargins(
            18,
            18,
            18,
            18
        )

        table_layout.setSpacing(
            12
        )

        table_layout.addWidget(
            self.section_title(
                "PROBE MAP"
            )
        )

        self.al_table = QtWidgets.QTableWidget()

        self.al_table.setColumnCount(
            4
        )

        self.al_table.setHorizontalHeaderLabels(
            [
                "POINT",
                "X",
                "Y",
                "SURFACE Z"
            ]
        )

        self.al_table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )

        self.al_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )

        self.al_table.horizontalHeader().setStretchLastSection(
            True
        )

        self.al_table.verticalHeader().setVisible(
            False
        )

        self.al_table.setMinimumHeight(
            220
        )

        table_layout.addWidget(
            self.al_table
        )

        # -----------------------------------------------------
        # 3D SURFACE HEAT MAP
        # -----------------------------------------------------

        heatmap_card = self.make_card()

        heatmap_layout = QtWidgets.QVBoxLayout(
            heatmap_card
        )

        heatmap_layout.setContentsMargins(
            18,
            18,
            18,
            18
        )

        heatmap_layout.setSpacing(
            10
        )

        heatmap_header = QtWidgets.QHBoxLayout()

        heatmap_header.addWidget(
            self.section_title(
                "3D SURFACE HEAT MAP"
            )
        )

        heatmap_header.addStretch()

        self.al_heatmap_status = QtWidgets.QLabel(
            "NO SURFACE DATA"
        )

        self.al_heatmap_status.setObjectName(
            "SmallLabel"
        )

        heatmap_header.addWidget(
            self.al_heatmap_status
        )

        heatmap_layout.addLayout(
            heatmap_header
        )

        heatmap_buttons = QtWidgets.QHBoxLayout()

        heatmap_buttons.setSpacing(
            8
        )

        self.al_heatmap_top_btn = QtWidgets.QPushButton(
            "TOP"
        )

        self.al_heatmap_iso_btn = QtWidgets.QPushButton(
            "ISO"
        )

        self.al_heatmap_fit_btn = QtWidgets.QPushButton(
            "FIT"
        )

        self.al_heatmap_clear_btn = QtWidgets.QPushButton(
            "CLEAR"
        )

        for button in [
            self.al_heatmap_top_btn,
            self.al_heatmap_iso_btn,
            self.al_heatmap_fit_btn,
            self.al_heatmap_clear_btn
        ]:

            button.setFixedWidth(
                65
            )

            heatmap_buttons.addWidget(
                button
            )

        heatmap_buttons.addStretch()

        heatmap_layout.addLayout(
            heatmap_buttons
        )

        self.al_heatmap_view = gl.GLViewWidget()

        self.al_heatmap_view.setBackgroundColor(
            (8, 8, 8)
        )

        self.al_heatmap_view.setMinimumHeight(
            430
        )

        self.al_heatmap_view.setCameraPosition(
            distance=180,
            elevation=30,
            azimuth=-45
        )

        heatmap_layout.addWidget(
            self.al_heatmap_view,
            1
        )

        self.al_heatmap_grid = gl.GLGridItem()

        self.al_heatmap_grid.setSize(
            200,
            200
        )

        self.al_heatmap_grid.setSpacing(
            10,
            10
        )

        self.al_heatmap_view.addItem(
            self.al_heatmap_grid
        )

        self.al_heatmap_surface = gl.GLMeshItem(
            smooth=False,
            drawEdges=True,
            drawFaces=True,
            edgeColor=(0.20, 0.20, 0.20, 0.65)
        )

        self.al_heatmap_view.addItem(
            self.al_heatmap_surface
        )

        self.al_heatmap_points = gl.GLScatterPlotItem(
            pos=np.empty(
                (0, 3),
                dtype=float
            ),
            size=7,
            color=(1.0, 1.0, 1.0, 1.0),
            pxMode=True
        )

        self.al_heatmap_view.addItem(
            self.al_heatmap_points
        )

        heatmap_legend = QtWidgets.QHBoxLayout()

        heatmap_legend.addWidget(
            self.small_label(
                "LOW Z"
            )
        )

        self.al_heatmap_legend = QtWidgets.QLabel(
            "BLUE  →  CYAN  →  GREEN  →  YELLOW  →  RED"
        )

        self.al_heatmap_legend.setAlignment(
            QtCore.Qt.AlignCenter
        )

        self.al_heatmap_legend.setStyleSheet(
            "color:#dddddd;"
            "font-weight:bold;"
        )

        heatmap_legend.addWidget(
            self.al_heatmap_legend,
            1
        )

        heatmap_legend.addWidget(
            self.small_label(
                "HIGH Z"
            )
        )

        heatmap_layout.addLayout(
            heatmap_legend
        )

        self.al_heatmap_top_btn.clicked.connect(
            self.autolevel_heatmap_top
        )

        self.al_heatmap_iso_btn.clicked.connect(
            self.autolevel_heatmap_iso
        )

        self.al_heatmap_fit_btn.clicked.connect(
            self.autolevel_heatmap_fit
        )

        self.al_heatmap_clear_btn.clicked.connect(
            self.clear_autolevel_heatmap
        )

        # Keep the table as the numerical probe data below the visual.
        al_main.addWidget(
            heatmap_card
        )

        al_main.addWidget(
            table_card
        )

        # -----------------------------------------------------
        # BOTTOM SPACE
        # -----------------------------------------------------

        al_main.addSpacing(
            20
        )

        # -----------------------------------------------------
        # FINISH AUTOLEVEL CONTENT
        # -----------------------------------------------------

        autolevel_scroll.setWidgetResizable(
            True
        )

        autolevel_scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarAlwaysOff
        )

        autolevel_scroll.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarAsNeeded
        )

        autolevel_scroll.setFrameShape(
            QtWidgets.QFrame.NoFrame
        )

        # Put the complete AUTOLEVEL content inside
        # the page scroll area.

        autolevel_scroll.setWidget(
            autolevel_content
        )

        # -----------------------------------------------------
        # AUTOLEVEL PAGE LAYOUT
        # -----------------------------------------------------

        autolevel_page_layout = QtWidgets.QVBoxLayout(
            autolevel_page
        )

        autolevel_page_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        autolevel_page_layout.setSpacing(
            0
        )

        autolevel_page_layout.addWidget(
            autolevel_scroll
        )

        # -----------------------------------------------------
        # ADD AUTOLEVEL TAB
        # -----------------------------------------------------

        tabs.addTab(
            autolevel_page,
            "AUTOLEVEL"
        )

        # =====================================================
        # GCODE TAB
        # =====================================================

        gcode_page = QtWidgets.QWidget()

        gp = QtWidgets.QVBoxLayout(
            gcode_page
        )

        gcode_header = QtWidgets.QHBoxLayout()

        gcode_header.addWidget(
            self.section_title(
                "G-CODE PROGRAM"
            )
        )

        gcode_header.addStretch()

        self.gcode_line_label = QtWidgets.QLabel(
            "LINE 0 / 0"
        )

        self.gcode_line_label.setObjectName(
            "Value"
        )

        gcode_header.addWidget(
            self.gcode_line_label
        )

        gp.addLayout(
            gcode_header
        )

        self.gcode_editor = GCodeEditor()

        gp.addWidget(
            self.gcode_editor,
            1
        )

        tabs.addTab(
            gcode_page,
            "G-CODE"
        )

        # =====================================================
        # CONSOLE TAB
        # =====================================================

        console_page = QtWidgets.QWidget()

        cp = QtWidgets.QVBoxLayout(
            console_page
        )

        console_header = QtWidgets.QHBoxLayout()

        console_header.addWidget(
            self.section_title(
                "GRBL CONSOLE"
            )
        )

        console_header.addStretch()

        self.clear_console_btn = QtWidgets.QPushButton(
            "CLEAR"
        )

        self.clear_console_btn.setFixedWidth(
            70
        )

        console_header.addWidget(
            self.clear_console_btn
        )

        cp.addLayout(
            console_header
        )

        self.log_box = QtWidgets.QTextEdit()

        self.log_box.setReadOnly(
            True
        )

        cp.addWidget(
            self.log_box,
            1
        )

        command_row = QtWidgets.QHBoxLayout()

        self.cmd_input = QtWidgets.QLineEdit()

        self.cmd_input.setPlaceholderText(
            "Manual GRBL command..."
        )

        self.cmd_send_btn = QtWidgets.QPushButton(
            "SEND"
        )

        command_row.addWidget(
            self.cmd_input,
            1
        )

        command_row.addWidget(
            self.cmd_send_btn
        )

        cp.addLayout(
            command_row
        )

        self.cmd_send_btn.clicked.connect(
            self.send_manual_command
        )

        self.cmd_input.returnPressed.connect(
            self.send_manual_command
        )

        self.clear_console_btn.clicked.connect(
            self.log_box.clear
        )

        tabs.addTab(
            console_page,
            "CONSOLE"
        )

        right.addWidget(
            tabs,
            1
        )

        # =====================================================
        # FOOTER
        # =====================================================

        footer = QtWidgets.QLabel(
            "MAD HAT  •  CNC CONTROL SOFTWARE  •  "
            "CNC / LASER / 3D PRINTING"
        )

        footer.setAlignment(
            QtCore.Qt.AlignCenter
        )

        footer.setStyleSheet("""
            QLabel {
                color: #555555;
                font-size: 8pt;
                padding: 3px;
            }
        """)

        main.addWidget(
            footer
        )

        self.update_button_state()

    # =========================================================
    # HELPERS
    # =========================================================

    def make_card(self):

        frame = QtWidgets.QFrame()

        frame.setObjectName(
            "Card"
        )

        return frame

    def section_title(self, text):

        label = QtWidgets.QLabel(
            text
        )

        label.setObjectName(
            "SectionTitle"
        )

        return label

    def small_label(self, text):

        label = QtWidgets.QLabel(
            text
        )

        label.setObjectName(
            "SmallLabel"
        )

        return label

    def make_value_label(self, text):

        label = QtWidgets.QLabel(
            text
        )

        label.setObjectName(
            "Value"
        )

        return label

    def make_double(
        self,
        value,
        minimum,
        maximum,
        decimals=3
    ):

        box = QtWidgets.QDoubleSpinBox()

        box.setRange(
            minimum,
            maximum
        )

        box.setDecimals(
            decimals
        )

        box.setSingleStep(
            0.1
        )

        box.setValue(
            value
        )

        box.setEnabled(
            True
        )

        box.setReadOnly(
            False
        )

        box.setKeyboardTracking(
            True
        )

        box.setFocusPolicy(
            QtCore.Qt.StrongFocus
        )

        box.setButtonSymbols(
            QtWidgets.QAbstractSpinBox.UpDownArrows
        )

        box.setAlignment(
            QtCore.Qt.AlignRight
        )

        box.setMinimumHeight(
            30
        )

        box.setStyleSheet(
            """
            QDoubleSpinBox {
                background: #202020;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 30px;
            }

            QDoubleSpinBox:focus {
                background: #202020;
                color: #ffffff;
                border: 1px solid #f0a500;
            }

            QDoubleSpinBox:hover {
                border: 1px solid #666666;
            }

            QDoubleSpinBox::up-button {
                background: #303030;
                border: none;
                width: 16px;
            }

            QDoubleSpinBox::down-button {
                background: #303030;
                border: none;
                width: 16px;
            }

            QDoubleSpinBox::up-button:hover,
            QDoubleSpinBox::down-button:hover {
                background: #404040;
            }

            QDoubleSpinBox QLineEdit {
                background: transparent;
                color: #ffffff;
                selection-background-color: #f0a500;
                selection-color: #111111;
                border: none;
            }
            """
        )

        line_edit = box.lineEdit()

        if line_edit:

            line_edit.setReadOnly(
                False
            )

            line_edit.setEnabled(
                True
            )

            line_edit.setFocusPolicy(
                QtCore.Qt.StrongFocus
            )

            line_edit.setStyleSheet(
                """
                QLineEdit {
                    background: transparent;
                    color: #ffffff;
                    border: none;
                    selection-background-color: #f0a500;
                    selection-color: #111111;
                }
                """
            )

        return box

    # =========================================================
    # DRO
    # =========================================================

    def make_dro(self, axis):

        layout = QtWidgets.QVBoxLayout()

        title = QtWidgets.QLabel(
            axis
        )

        title.setObjectName(
            "SmallLabel"
        )

        value = QtWidgets.QLabel(
            "0.000"
        )

        value.setObjectName(
            "BigDRO"
        )

        if axis == "X":
            self.dro_x_value = value

        elif axis == "Y":
            self.dro_y_value = value

        elif axis == "Z":
            self.dro_z_value = value

        layout.addWidget(
            title
        )

        layout.addWidget(
            value
        )

        return layout

    # =========================================================
    # JOG BUTTON
    # =========================================================

    def make_jog(self, direction):

        button = QtWidgets.QPushButton(
            direction
        )

        button.setObjectName(
            "Jog"
        )

        button.clicked.connect(
            lambda checked=False,
            d=direction:
            self.jog(d)
        )

        self.jog_buttons.append(
            button
        )

        return button

    # =========================================================
    # STYLE
    # =========================================================

    def apply_styles(self):

        self.setStyleSheet(
            APP_STYLE
        )

    # =========================================================
    # PORTS
    # =========================================================

    def refresh_ports(self):

        if not hasattr(
            self,
            "port_box"
        ):
            return

        current = self.port_box.currentText()

        self.port_box.clear()

        for port in serial.tools.list_ports.comports():

            description = port.description or ""

            text = (
                f"{port.device} - "
                f"{description}"
            )

            self.port_box.addItem(
                text,
                port.device
            )

        if current:

            for i in range(
                self.port_box.count()
            ):

                if (
                    self.port_box.itemText(i)
                    == current
                ):

                    self.port_box.setCurrentIndex(
                        i
                    )

                    break

    # =========================================================
    # SELECTED PORT
    # =========================================================

    def selected_port(self):

        data = self.port_box.currentData()

        if data:
            return data

        text = self.port_box.currentText()

        return text.split(
            " - "
        )[0]

    # =========================================================
    # CONNECT
    # =========================================================

    def connect(self):

        if self.ser:
            return

        port = self.selected_port()

        if not port:

            self.log(
                "NO SERIAL PORT SELECTED"
            )

            return

        baud = int(
            self.baud_box.currentText()
        )

        try:

            self.ser = serial.Serial(
                port=port,
                baudrate=baud,
                timeout=0.05,
                write_timeout=1
            )

            time.sleep(2)

            self.ser.reset_input_buffer()

            self.log(
                f"CONNECTED: {port} @ {baud}"
            )

            try:

                QSound.play(
                    "Assets/connected.wav"
                )

            except Exception:
                pass

            self.connect_btn.setEnabled(
                False
            )

            self.disconnect_btn.setEnabled(
                True
            )

            self.status_timer.start(
                100
            )

            self.update_button_state()

            self.request_status()

        except Exception as e:

            self.ser = None

            self.log(
                f"CONNECTION ERROR: {e}"
            )

    # =========================================================
    # DISCONNECT
    # =========================================================

    def disconnect(self):

        if (
            self.sender
            and
            self.sender.isRunning()
        ):

            self.log(
                "STOP THE CURRENT JOB FIRST"
            )

            return

        if (
            self.autolevel_worker
            and
            self.autolevel_worker.isRunning()
        ):

            self.log(
                "STOP AUTOLEVEL FIRST"
            )

            return

        if self.ser:

            try:
                self.ser.close()

            except Exception:
                pass

            self.ser = None

        self.status_timer.stop()

        self.connect_btn.setEnabled(
            True
        )

        self.disconnect_btn.setEnabled(
            False
        )

        self.state_label.setText(
            "DISCONNECTED"
        )

        self.header_status.setText(
            "● DISCONNECTED"
        )

        self.update_button_state()

        self.log(
            "DISCONNECTED"
        )

        try:

            QSound.play(
                "Assets/disconnected.wav"
            )

        except Exception:
            pass

    # =========================================================
    # LOAD GCODE
    # =========================================================

    def load_gcode(self, path=None):

        if not path:

            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Load G-code",
                "",
                "G-code (*.nc *.gcode *.tap *.ngc *.txt)"
            )

        if not path:
            return

        try:

            with open(
                path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as file:

                self.gcode_lines = file.readlines()

        except Exception as e:

            self.log(
                f"LOAD ERROR: {e}"
            )

            return

        self.original_gcode_lines = list(
            self.gcode_lines
        )

        self.gcode_is_levelled = False

        self.current_file = path

        filename = os.path.basename(
            path
        )

        self.file_label.setText(
            f"{filename}\n"
            f"{len(self.gcode_lines):,} lines"
        )

        self.gcode_editor.setPlainText(
            "".join(
                self.gcode_lines
            )
        )

        self.gcode_editor.clear_highlight()

        self.gcode_line_label.setText(
            f"LINE 0 / "
            f"{len(self.gcode_lines):,}"
        )

        self.log(
            f"LOADED: {filename}"
        )

        self.plot_gcode()

        self.progress_bar.setValue(
            0
        )

        self.run_time_label.setText(
            "RUN 00:00:00"
        )

        self.eta_label.setText(
            "ETA --:--:--"
        )

        self.update_button_state()

    # =========================================================
    # DRAG DROP
    # =========================================================

    def dragEnterEvent(self, event):

        if event.mimeData().hasUrls():

            event.acceptProposedAction()

    def dropEvent(self, event):

        for url in event.mimeData().urls():

            path = url.toLocalFile()

            if path.lower().endswith(
                (
                    ".nc",
                    ".gcode",
                    ".tap",
                    ".ngc",
                    ".txt"
                )
            ):

                self.load_gcode(
                    path
                )

                break

    # =========================================================
    # CLEAR GCODE
    # =========================================================

    def clear_gcode(self):

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        if (
            self.autolevel_worker
            and
            self.autolevel_worker.isRunning()
        ):
            return

        self.gcode_lines = []
        self.original_gcode_lines = []
        self.current_file = ""

        self.gcode_is_levelled = False

        self.file_label.setText(
            "No file loaded"
        )

        self.gcode_editor.clear()
        self.gcode_editor.clear_highlight()

        self.gcode_line_label.setText(
            "LINE 0 / 0"
        )

        self.progress_bar.setValue(
            0
        )

        self.clear_visualiser()

        self.update_button_state()

    # =========================================================
    # PLAY
    # =========================================================

    def play(self):

        if not self.ser:

            self.log(
                "NOT CONNECTED"
            )

            return

        if not self.gcode_lines:

            self.log(
                "NO G-CODE LOADED"
            )

            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        if (
            self.autolevel_worker
            and
            self.autolevel_worker.isRunning()
        ):
            return

        self.is_paused = False

        self.job_start_time = time.time()

        self.progress_bar.setValue(
            0
        )

        self.gcode_editor.clear_highlight()

        self.gcode_line_label.setText(
            f"LINE 0 / "
            f"{len(self.gcode_lines):,}"
        )

        self.run_time_label.setText(
            "RUN 00:00:00"
        )

        self.eta_label.setText(
            "ETA calculating..."
        )

        self.sender = SenderThread(
            self.ser,
            self.gcode_lines
        )

        self.sender.log_signal.connect(
            self.log
        )

        self.sender.progress_signal.connect(
            self.progress_bar.setValue
        )

        self.sender.line_signal.connect(
            self.highlight_gcode_line
        )

        self.sender.feed_signal.connect(
            lambda value:
            self.feed_label.setText(
                f"F {value:.0f}"
            )
        )

        self.sender.speed_signal.connect(
            lambda value:
            self.speed_label.setText(
                f"S {value:.0f}"
            )
        )

        self.sender.status_signal.connect(
            self.update_tool_position
        )

        self.sender.machine_state_signal.connect(
            self.update_machine_state
        )

        self.sender.done_signal.connect(
            self.job_finished
        )

        self.sender.stopped_signal.connect(
            self.job_stopped
        )

        self.sender.error_signal.connect(
            self.handle_sender_error
        )

        self.sender.finished.connect(
            self.thread_finished
        )

        self.status_timer.stop()

        self.progress_timer.start(
            200
        )

        self.sender.start()

        self.update_button_state()

        self.log(
            "JOB STARTED"
        )

    # =========================================================
    # PAUSE
    # =========================================================

    def pause_job(self):

        if not self.ser:
            return

        if (
            not self.sender
            or
            not self.sender.isRunning()
        ):
            return

        try:

            self.ser.write(
                b"!"
            )

            self.is_paused = True

            self.log(
                "FEED HOLD / PAUSED"
            )

        except Exception as e:

            self.log(
                f"PAUSE ERROR: {e}"
            )

        self.update_button_state()

    # =========================================================
    # RESUME
    # =========================================================

    def resume_job(self):

        if not self.ser:
            return

        try:

            self.ser.write(
                b"~"
            )

            self.is_paused = False

            self.log(
                "CYCLE START / RESUMED"
            )

        except Exception as e:

            self.log(
                f"RESUME ERROR: {e}"
            )

        self.update_button_state()

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):

        if not self.ser:
            return

        if (
            not self.sender
            or
            not self.sender.isRunning()
        ):
            return

        answer = QtWidgets.QMessageBox.warning(
            self,
            "Stop Job",
            "STOP the current CNC job?\n\n"
            "The current job will be aborted and "
            "cannot be resumed from the same line.",
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No
        )

        if answer != QtWidgets.QMessageBox.Yes:
            return

        self.log(
            "STOPPING JOB..."
        )

        if self.sender:

            self.sender.stop()

        try:

            self.ser.write(
                b"\x18"
            )

            self.ser.flush()

        except Exception as e:

            self.log(
                f"STOP RESET ERROR: {e}"
            )

        if self.sender:

            if not self.sender.wait(1500):

                self.log(
                    "WARNING: SENDER THREAD DID NOT EXIT CLEANLY"
                )

        self.is_paused = False

        self.progress_timer.stop()

        self.stop_btn.setEnabled(
            False
        )

        self.pause_btn.setEnabled(
            False
        )

        self.resume_btn.setEnabled(
            False
        )

        self.eta_label.setText(
            "ETA --:--:--"
        )

        try:

            self.ser.reset_input_buffer()

        except Exception:
            pass

        if self.ser and self.ser.is_open:

            self.status_timer.start(
                100
            )

            QtCore.QTimer.singleShot(
                250,
                self.request_status
            )

        self.log(
            "JOB ABORTED / GRBL RESET"
        )

        self.update_button_state()

    # =========================================================
    # SOFT RESET
    # =========================================================

    def soft_reset(self):

        if not self.ser:
            return

        answer = QtWidgets.QMessageBox.warning(
            self,
            "Soft Reset",
            "Send GRBL SOFT RESET (Ctrl-X)?\n\n"
            "The controller will reset and the "
            "current motion/job will stop.",
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No
        )

        if answer != QtWidgets.QMessageBox.Yes:
            return

        if self.sender:

            self.sender.stop()

        if (
            self.autolevel_worker
            and
            self.autolevel_worker.isRunning()
        ):

            self.autolevel_worker.stop()

        try:

            self.ser.write(
                b"\x18"
            )

            self.ser.flush()

            self.log(
                "GRBL SOFT RESET SENT"
            )

        except Exception as e:

            self.log(
                f"RESET ERROR: {e}"
            )

        if self.sender:

            self.sender.wait(
                1500
            )

        if self.autolevel_worker:

            self.autolevel_worker.wait(
                1500
            )

        self.is_paused = False

        self.progress_timer.stop()

        try:

            self.ser.reset_input_buffer()

        except Exception:
            pass

        if self.ser and self.ser.is_open:

            self.status_timer.start(
                100
            )

            QtCore.QTimer.singleShot(
                250,
                self.request_status
            )

        self.update_button_state()

    # =========================================================
    # CHECK GCODE
    # =========================================================

    def check_gcode(self):

        if not self.gcode_lines:

            self.log(
                "NO G-CODE LOADED"
            )

            return

        errors = []

        for i, line in enumerate(
            self.gcode_lines
        ):

            clean = re.sub(
                r"\([^)]*\)",
                "",
                line
            )

            clean = clean.split(
                ";"
            )[0].strip()

            if not clean:
                continue

            if any(
                char in clean
                for char in [
                    "{",
                    "}",
                    "[",
                    "]"
                ]
            ):

                errors.append(
                    (
                        i + 1,
                        clean
                    )
                )

        if errors:

            self.log(
                f"G-CODE CHECK: "
                f"{len(errors)} suspicious lines"
            )

            for number, line in errors[:10]:

                self.log(
                    f"LINE {number}: {line}"
                )

        else:

            self.log(
                "G-CODE CHECK PASSED"
            )

            QtWidgets.QMessageBox.information(
                self,
                "G-code Check",
                "Basic G-code validation passed."
            )

    # =========================================================
    # JOB COMPLETE
    # =========================================================

    def job_finished(self):

        self.progress_bar.setValue(
            100
        )

        self.progress_timer.stop()

        self.eta_label.setText(
            "ETA 00:00:00"
        )

        self.is_paused = False

        self.stop_btn.setEnabled(
            False
        )

        self.resume_btn.setEnabled(
            False
        )

        if self.ser:
            self.status_timer.start(
                100
            )

        self.update_button_state()

        self.log(
            "JOB COMPLETE"
        )

        try:

            QSound.play(
                "Assets/job_complete.wav"
            )

        except Exception:
            pass

    # =========================================================
    # JOB STOPPED
    # =========================================================

    def job_stopped(self):

        self.progress_timer.stop()

        self.stop_btn.setEnabled(
            False
        )

        self.pause_btn.setEnabled(
            False
        )

        self.resume_btn.setEnabled(
            False
        )

        self.is_paused = False

        if self.ser and self.ser.is_open:

            self.status_timer.start(
                100
            )

            QtCore.QTimer.singleShot(
                250,
                self.request_status
            )

        self.update_button_state()

        self.log(
            "JOB STOPPED"
        )

    # =========================================================
    # THREAD CLEANUP
    # =========================================================

    def thread_finished(self):

        if self.sender:

            self.sender.deleteLater()

            self.sender = None

        self.update_button_state()

    # =========================================================
    # ERROR
    # =========================================================

    def handle_sender_error(self, message):

        self.log(
            message
        )

        self.update_button_state()

    # =========================================================
    # PROGRESS
    # =========================================================

    def update_progress_info(self):

        if not self.job_start_time:
            return

        elapsed = int(
            time.time()
            -
            self.job_start_time
        )

        self.run_time_label.setText(
            f"RUN {self.format_time(elapsed)}"
        )

        progress = self.progress_bar.value()

        if progress > 1:

            total = (
                elapsed
                *
                100
                /
                progress
            )

            eta = max(
                0,
                int(
                    total
                    -
                    elapsed
                )
            )

            self.eta_label.setText(
                f"ETA {self.format_time(eta)}"
            )

        else:

            self.eta_label.setText(
                "ETA calculating..."
            )

    @staticmethod
    def format_time(seconds):

        h, remainder = divmod(
            int(seconds),
            3600
        )

        m, s = divmod(
            remainder,
            60
        )

        return (
            f"{h:02}:"
            f"{m:02}:"
            f"{s:02}"
        )

    # =========================================================
    # STATUS REQUEST
    # =========================================================

    def request_status(self):

        if not self.ser:
            return

        try:

            self.ser.write(
                b"?"
            )

        except Exception:
            pass

    # =========================================================
    # STATUS POLLING
    # =========================================================

    def poll_status(self):

        if not self.ser:
            return

        if not self.ser.is_open:
            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        if (
            self.autolevel_worker
            and
            self.autolevel_worker.isRunning()
        ):
            return

        try:

            self.ser.write(
                b"?"
            )

            while self.ser.in_waiting:

                line = (
                    self.ser.readline()
                    .decode(
                        errors="ignore"
                    )
                    .strip()
                )

                if line.startswith("<"):

                    self.parse_status(
                        line
                    )

                elif line:

                    self.log(
                        f"<< {line}"
                    )

        except serial.SerialException as e:

            self.log(
                f"STATUS ERROR: {e}"
            )

    # =========================================================
    # STATUS PARSER
    # =========================================================

    def parse_status(self, status):

        state = re.match(
            r"<([^|,]+)",
            status
        )

        if state:

            self.update_machine_state(
                state.group(1)
            )

        mpos = re.search(
            r"MPos:([-0-9.]+),([-0-9.]+),([-0-9.]+)",
            status
        )

        wpos = re.search(
            r"WPos:([-0-9.]+),([-0-9.]+),([-0-9.]+)",
            status
        )

        wco = re.search(
            r"WCO:([-0-9.]+),([-0-9.]+),([-0-9.]+)",
            status
        )

        if wco:

            self.last_wco = list(
                map(
                    float,
                    wco.groups()
                )
            )

        x = y = z = 0.0

        if wpos:

            x, y, z = map(
                float,
                wpos.groups()
            )

        elif mpos and self.last_wco:

            mx, my, mz = map(
                float,
                mpos.groups()
            )

            x = mx - self.last_wco[0]
            y = my - self.last_wco[1]
            z = mz - self.last_wco[2]

        elif mpos:

            x, y, z = map(
                float,
                mpos.groups()
            )

        self.update_tool_position(
            x,
            y,
            z
        )

        fs = re.search(
            r"FS:([0-9.]+),([0-9.]+)",
            status
        )

        if fs:

            self.feed_label.setText(
                f"F {float(fs.group(1)):.0f}"
            )

            self.speed_label.setText(
                f"S {float(fs.group(2)):.0f}"
            )

    # =========================================================
    # MACHINE STATE
    # =========================================================

    def update_machine_state(self, state):

        state = state.upper()

        self.state_label.setText(
            state
        )

        self.header_status.setText(
            f"● {state}"
        )

        if "ALARM" in state:

            self.header_status.setStyleSheet(
                "color:#ff4444;"
                "font-size:12pt;"
                "font-weight:bold;"
            )

        elif "RUN" in state:

            self.header_status.setStyleSheet(
                "color:#55dd55;"
                "font-size:12pt;"
                "font-weight:bold;"
            )

        elif "HOLD" in state:

            self.header_status.setStyleSheet(
                "color:#f0a500;"
                "font-size:12pt;"
                "font-weight:bold;"
            )

        else:

            self.header_status.setStyleSheet(
                "color:#f0a500;"
                "font-size:12pt;"
                "font-weight:bold;"
            )

    # =========================================================
    # TOOL POSITION
    # =========================================================

    def update_tool_position(self, x, y, z):

        self.dro_x_value.setText(
            f"{x:.3f}"
        )

        self.dro_y_value.setText(
            f"{y:.3f}"
        )

        self.dro_z_value.setText(
            f"{z:.3f}"
        )

        # Apply the same preview-only Z offset as the loaded G-code
        # so the live red tool-position dot stays aligned with the
        # shifted toolpath and does not appear below the grid.
        preview_z = z + getattr(
            self,
            "preview_z_offset",
            0.0
        )

        self.tool_3d.setData(
            pos=np.array(
                [[x, y, preview_z]],
                dtype=float
            )
        )

    # =========================================================
    # JOG
    # =========================================================

    def jog(self, direction):

        if not self.ser:
            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        if (
            self.autolevel_worker
            and
            self.autolevel_worker.isRunning()
        ):
            return

        distance = float(
            self.jog_distance_box.currentText()
        )

        speed = self.jog_speed_box.value()

        axis = direction[0]

        sign = (
            "+"
            if direction[1] == "+"
            else "-"
        )

        distance_text = f"{distance:g}"

        if sign == "-":

            distance_text = "-" + distance_text

        command = (
            f"$J=G91 {axis}"
            f"{distance_text} "
            f"F{speed}\n"
        )

        try:

            self.ser.write(
                command.encode()
            )

            self.log(
                f"JOG {direction}  "
                f"{distance:g} mm  "
                f"{speed} mm/min"
            )

        except Exception as e:

            self.log(
                f"JOG ERROR: {e}"
            )

    # =========================================================
    # ZERO AXIS
    # =========================================================

    def zero_axis(self, axis):

        if not self.ser:
            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        try:

            command = (
                f"G10 L20 P1 {axis}0\n"
            )

            self.ser.write(
                command.encode()
            )

            self.log(
                f"{axis} WORK ZERO SET"
            )

            self.request_status()

        except Exception as e:

            self.log(
                f"ZERO ERROR: {e}"
            )

    # =========================================================
    # ZERO ALL
    # =========================================================

    def zero_all(self):

        if not self.ser:
            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        try:

            self.ser.write(
                b"G10 L20 P1 X0 Y0 Z0\n"
            )

            self.log(
                "X/Y/Z WORK ZERO SET"
            )

            self.request_status()

        except Exception as e:

            self.log(
                f"ZERO ALL ERROR: {e}"
            )

    # =========================================================
    # GO TO ZERO
    # =========================================================

    def go_zero(self):

        if not self.ser:
            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        answer = QtWidgets.QMessageBox.warning(
            self,
            "Go To Zero",
            "Move the machine to X0 Y0 Z0?\n\n"
            "Make sure the travel path is clear.",
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No
        )

        if answer != QtWidgets.QMessageBox.Yes:
            return

        self.send_command(
            "G90 G0 X0 Y0 Z0"
        )

    # =========================================================
    # HOME
    # =========================================================

    def home_machine(self):

        if not self.ser:
            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):
            return

        answer = QtWidgets.QMessageBox.warning(
            self,
            "Home Machine",
            "Send $H to GRBL?\n\n"
            "Make sure the machine is clear "
            "before homing.",
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No
        )

        if answer == QtWidgets.QMessageBox.Yes:

            self.send_command(
                "$H"
            )

    # =========================================================
    # SPINDLE CW
    # =========================================================

    def spindle_cw(self):

        rpm = self.rpm_box.value()

        self.send_command(
            f"M3 S{rpm}"
        )

    # =========================================================
    # SPINDLE CCW
    # =========================================================

    def spindle_ccw(self):

        rpm = self.rpm_box.value()

        self.send_command(
            f"M4 S{rpm}"
        )

    # =========================================================
    # FEED OVERRIDE
    # =========================================================

    def feed_override_change(self, amount):

        if not self.ser:
            return

        new_value = max(
            10,
            min(
                200,
                self.feed_override + amount
            )
        )

        while self.feed_override < new_value:

            try:

                self.ser.write(
                    b"\x91"
                )

            except Exception:
                break

            self.feed_override += 10

        while self.feed_override > new_value:

            try:

                self.ser.write(
                    b"\x90"
                )

            except Exception:
                break

            self.feed_override -= 10

        self.feed_override_label.setText(
            f"{self.feed_override}%"
        )

    def feed_override_set(self, value):

        if not self.ser:
            return

        self.feed_override = 100

        try:

            self.ser.write(
                b"\x92"
            )

        except Exception:
            pass

        self.feed_override_label.setText(
            "100%"
        )

    # =========================================================
    # SPINDLE OVERRIDE
    # =========================================================

    def spindle_override_change(self, amount):

        if not self.ser:
            return

        new_value = max(
            10,
            min(
                200,
                self.spindle_override + amount
            )
        )

        while self.spindle_override < new_value:

            try:

                self.ser.write(
                    b"\x9A"
                )

            except Exception:
                break

            self.spindle_override += 10

        while self.spindle_override > new_value:

            try:

                self.ser.write(
                    b"\x99"
                )

            except Exception:
                break

            self.spindle_override -= 10

        self.spindle_override_label.setText(
            f"{self.spindle_override}%"
        )

    def spindle_override_set(self, value):

        if not self.ser:
            return

        try:

            self.ser.write(
                b"\x9B"
            )

        except Exception:
            pass

        self.spindle_override = 100

        self.spindle_override_label.setText(
            "100%"
        )

    # =========================================================
    # MANUAL COMMAND
    # =========================================================

    def send_manual_command(self):

        if not self.ser:

            self.log(
                "NOT CONNECTED"
            )

            return

        if (
            self.autolevel_worker
            and
            self.autolevel_worker.isRunning()
        ):

            self.log(
                "AUTOLEVEL SCAN ACTIVE"
            )

            return

        command = (
            self.cmd_input.text()
            .strip()
        )

        if not command:
            return

        self.send_command(
            command
        )

        self.cmd_input.clear()

    # =========================================================
    # SEND COMMAND
    # =========================================================

    def send_command(self, command):

        if not self.ser:
            return

        if (
            self.autolevel_worker
            and
            self.autolevel_worker.isRunning()
        ):

            return

        try:

            self.ser.write(
                (
                    command
                    +
                    "\n"
                ).encode()
            )

            self.log(
                f">> {command}"
            )

        except Exception as e:

            self.log(
                f"COMMAND ERROR: {e}"
            )

    # =========================================================
    # GCODE HIGHLIGHT
    # =========================================================

    def highlight_gcode_line(self, line_number):

        self.gcode_editor.highlight_line(
            line_number
        )

        self.gcode_line_label.setText(
            f"LINE "
            f"{line_number + 1:,}"
            f" / "
            f"{len(self.gcode_lines):,}"
        )

    # =========================================================
    # =========================================================
    # AUTOLEVEL
    # =========================================================
    # =========================================================

    def start_autolevel(self):

        if not self.ser:

            self.log(
                "AUTOLEVEL: NOT CONNECTED"
            )

            return

        if not self.ser.is_open:

            self.log(
                "AUTOLEVEL: SERIAL PORT IS CLOSED"
            )

            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):

            self.log(
                "STOP THE CURRENT JOB FIRST"
            )

            return

        if (
            self.autolevel_worker
            and
            self.autolevel_worker.isRunning()
        ):
            return

        x_min = self.al_x_min.value()
        x_max = self.al_x_max.value()

        y_min = self.al_y_min.value()
        y_max = self.al_y_max.value()

        z_min = self.al_z_min.value()
        z_max = self.al_z_max.value()

        resolution = self.al_resolution.value()

        probe_feed = self.al_probe_feed.value()

        z_retract = self.al_z_retract.value()

        if x_min >= x_max:

            QtWidgets.QMessageBox.warning(
                self,
                "AutoLevel",
                "X MIN must be less than X MAX."
            )

            return

        if y_min >= y_max:

            QtWidgets.QMessageBox.warning(
                self,
                "AutoLevel",
                "Y MIN must be less than Y MAX."
            )

            return

        if z_min >= z_max:

            QtWidgets.QMessageBox.warning(
                self,
                "AutoLevel",
                "Z MIN must be less than Z MAX."
            )

            return

        if resolution <= 0:

            QtWidgets.QMessageBox.warning(
                self,
                "AutoLevel",
                "Resolution must be greater than zero."
            )

            return

        if probe_feed <= 0:

            QtWidgets.QMessageBox.warning(
                self,
                "AutoLevel",
                "Probe feed must be greater than zero."
            )

            return

        # -----------------------------------------------------
        # Calculate number of points
        # -----------------------------------------------------

        x_count = (
            int(
                np.ceil(
                    (x_max - x_min)
                    /
                    resolution
                )
            )
            +
            1
        )

        y_count = (
            int(
                np.ceil(
                    (y_max - y_min)
                    /
                    resolution
                )
            )
            +
            1
        )

        total = (
            x_count
            *
            y_count
        )

        warning = (
            f"AutoLevel will probe approximately "
            f"{total} points.\n\n"
            f"X: {x_min:.3f} to {x_max:.3f} mm\n"
            f"Y: {y_min:.3f} to {y_max:.3f} mm\n"
            f"Probe Z range: {z_min:.3f} to {z_max:.3f} mm\n"
            f"Resolution: {resolution:.3f} mm\n"
            f"Probe feed: {probe_feed:.1f} mm/min\n"
            f"Retract: {z_retract:.3f} mm\n\n"
            f"Make sure the probe is connected and "
            f"the scan area is safe."
        )

        answer = QtWidgets.QMessageBox.warning(
            self,
            "Start AutoLevel Scan",
            warning,
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No
        )

        if answer != QtWidgets.QMessageBox.Yes:

            return

        # -----------------------------------------------------
        # Clear previous map
        # -----------------------------------------------------

        self.autolevel_points = []

        self.al_table.setRowCount(
            0
        )

        self.al_progress.setValue(
            0
        )

        self.al_point_label.setText(
            f"POINT 0 / {total}"
        )

        self.al_current_x.setText(
            "X 0.000"
        )

        self.al_current_y.setText(
            "Y 0.000"
        )

        self.al_current_z.setText(
            "Z 0.000"
        )

        self.autolevel_status_label.setText(
            "SCANNING..."
        )

        # -----------------------------------------------------
        # Stop status polling.
        # AutoLevel worker owns the serial port while scanning.
        # -----------------------------------------------------

        self.status_timer.stop()

        self.autolevel_worker = AutoLevelWorker(
            self.ser,
            x_min,
            x_max,
            y_min,
            y_max,
            z_min,
            z_max,
            resolution,
            probe_feed,
            z_retract,
            self.al_probe_x_offset.value(),
            self.al_probe_y_offset.value(),
            self.al_probe_z_offset.value()
        )

        self.autolevel_worker.log_signal.connect(
            self.log
        )

        self.autolevel_worker.progress_signal.connect(
            self.al_progress.setValue
        )

        self.autolevel_worker.point_signal.connect(
            self.autolevel_point_received
        )

        self.autolevel_worker.status_signal.connect(
            self.autolevel_status_label.setText
        )

        self.autolevel_worker.finished_signal.connect(
            self.autolevel_finished
        )

        self.autolevel_worker.stopped_signal.connect(
            self.autolevel_stopped
        )

        self.autolevel_worker.error_signal.connect(
            self.autolevel_error
        )

        self.autolevel_worker.finished.connect(
            self.autolevel_thread_finished
        )

        # Start the worker before refreshing button states.  If button
        # states are updated first, QThread.isRunning() is still False
        # and STOP SCAN remains disabled when the scan begins.
        self.autolevel_worker.start()

        # Enable STOP immediately; refresh again after the thread has
        # entered its running state to keep all controls in sync.
        self.al_scan_btn.setEnabled(False)
        self.al_stop_btn.setEnabled(True)
        self.al_clear_btn.setEnabled(False)

        QtCore.QTimer.singleShot(
            100,
            self.update_button_state
        )

        self.log(
            f"AUTOLEVEL: {total} probe points"
        )

    # =========================================================
    # AUTOLEVEL POINT
    # =========================================================

    def autolevel_point_received(
        self,
        point_number,
        total,
        x,
        y,
        z
    ):

        self.autolevel_points.append(
            {
                "x": float(x),
                "y": float(y),
                "z": float(z)
            }
        )

        self.al_point_label.setText(
            f"POINT {point_number} / {total}"
        )

        self.al_current_x.setText(
            f"X {x:.3f}"
        )

        self.al_current_y.setText(
            f"Y {y:.3f}"
        )

        self.al_current_z.setText(
            f"Z {z:.3f}"
        )

        row = self.al_table.rowCount()

        self.al_table.insertRow(
            row
        )

        values = [
            str(point_number),
            f"{x:.4f}",
            f"{y:.4f}",
            f"{z:.4f}"
        ]

        for column, value in enumerate(
            values
        ):

            self.al_table.setItem(
                row,
                column,
                QtWidgets.QTableWidgetItem(
                    value
                )
            )

        self.al_table.scrollToBottom()

        # Update the 3D heat map immediately after each probe.
        self.update_autolevel_heatmap()

    # =========================================================
    # AUTOLEVEL FINISHED
    # =========================================================

    def autolevel_finished(self, points):

        self.autolevel_points = list(
            points
        )

        self.al_progress.setValue(
            100
        )

        self.autolevel_status_label.setText(
            f"SURFACE MAP: "
            f"{len(self.autolevel_points)} POINTS"
        )

        if self.ser and self.ser.is_open:

            self.status_timer.start(
                100
            )

            QtCore.QTimer.singleShot(
                250,
                self.request_status
            )

        self.log(
            "AUTOLEVEL SURFACE MAP COMPLETE"
        )

        self.update_autolevel_heatmap()

        self.update_button_state()

    # =========================================================
    # AUTOLEVEL STOPPED
    # =========================================================

    def autolevel_stopped(self):

        self.al_progress.setValue(
            0
        )

        self.autolevel_status_label.setText(
            f"SCAN STOPPED - "
            f"{len(self.autolevel_points)} POINTS"
        )

        if self.ser and self.ser.is_open:

            self.status_timer.start(
                100
            )

            QtCore.QTimer.singleShot(
                250,
                self.request_status
            )

        self.log(
            "AUTOLEVEL SCAN STOPPED"
        )

        self.update_button_state()

    # =========================================================
    # AUTOLEVEL ERROR
    # =========================================================

    def autolevel_error(self, message):

        self.autolevel_status_label.setText(
            "SCAN ERROR"
        )

        self.log(
            f"AUTOLEVEL ERROR: {message}"
        )

        if self.ser and self.ser.is_open:

            self.status_timer.start(
                100
            )

            QtCore.QTimer.singleShot(
                250,
                self.request_status
            )

        QtWidgets.QMessageBox.critical(
            self,
            "AutoLevel Error",
            message
        )

        self.update_button_state()

    # =========================================================
    # AUTOLEVEL THREAD CLEANUP
    # =========================================================

    def autolevel_thread_finished(self):

        if self.autolevel_worker:

            self.autolevel_worker.deleteLater()

            self.autolevel_worker = None

        if self.ser and self.ser.is_open:

            if not self.status_timer.isActive():

                self.status_timer.start(
                    100
                )

        self.update_button_state()

    # =========================================================
    # STOP AUTOLEVEL
    # =========================================================

    def stop_autolevel(self):

        if (
            not self.autolevel_worker
            or
            not self.autolevel_worker.isRunning()
        ):

            return

        answer = QtWidgets.QMessageBox.warning(
            self,
            "Stop AutoLevel",
            "Stop the AutoLevel scan?\n\n"
            "GRBL will be soft-reset to abort the "
            "current probe movement.",
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No
        )

        if answer != QtWidgets.QMessageBox.Yes:

            return

        self.log(
            "STOPPING AUTOLEVEL..."
        )

        self.autolevel_worker.stop()

        # AutoLevelWorker.stop() sends the GRBL soft-reset itself.
        # Disable the button while the worker exits; thread cleanup
        # will refresh the controls when it has stopped.
        self.al_stop_btn.setEnabled(False)
        self.al_scan_btn.setEnabled(False)
        self.al_clear_btn.setEnabled(False)

    # CLEAR AUTOLEVEL
    # =========================================================

    def clear_autolevel(self):

        if (
            self.autolevel_worker
            and
            self.autolevel_worker.isRunning()
        ):
            return

        self.autolevel_points = []

        self.al_table.setRowCount(
            0
        )

        self.al_progress.setValue(
            0
        )

        self.al_point_label.setText(
            "POINT 0 / 0"
        )

        self.al_current_x.setText(
            "X 0.000"
        )

        self.al_current_y.setText(
            "Y 0.000"
        )

        self.al_current_z.setText(
            "Z 0.000"
        )

        self.autolevel_status_label.setText(
            "NO SURFACE MAP"
        )

        self.clear_autolevel_heatmap()

        self.log(
            "AUTOLEVEL MAP CLEARED"
        )

        self.update_button_state()

    # =========================================================
    # SAVE AUTOLEVEL
    # =========================================================

    def save_autolevel(self):

        if not self.autolevel_points:

            QtWidgets.QMessageBox.warning(
                self,
                "Save AutoLevel",
                "There is no probe map to save."
            )

            return

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save AutoLevel Surface Map",
            "",
            "AutoLevel Map (*.json)"
        )

        if not path:
            return

        data = {
            "version": 1,
            "x_min": self.al_x_min.value(),
            "x_max": self.al_x_max.value(),
            "y_min": self.al_y_min.value(),
            "y_max": self.al_y_max.value(),
            "z_min": self.al_z_min.value(),
            "z_max": self.al_z_max.value(),
            "resolution": self.al_resolution.value(),
            "probe_feed": self.al_probe_feed.value(),
            "z_retract": self.al_z_retract.value(),
            "z_surface": self.al_z_surface.value(),
            "probe_x_offset": self.al_probe_x_offset.value(),
            "probe_y_offset": self.al_probe_y_offset.value(),
            "probe_z_offset": self.al_probe_z_offset.value(),
            "points": self.autolevel_points
        }

        try:

            with open(
                path,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    data,
                    file,
                    indent=4
                )

            self.log(
                f"AUTOLEVEL MAP SAVED: "
                f"{os.path.basename(path)}"
            )

        except Exception as e:

            QtWidgets.QMessageBox.critical(
                self,
                "Save AutoLevel",
                str(e)
            )

    # =========================================================
    # LOAD AUTOLEVEL
    # =========================================================

    def load_autolevel(self):

        if (
            self.autolevel_worker
            and
            self.autolevel_worker.isRunning()
        ):
            return

        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load AutoLevel Surface Map",
            "",
            "AutoLevel Map (*.json)"
        )

        if not path:
            return

        try:

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(
                    file
                )

            points = data.get(
                "points",
                []
            )

            if not points:

                raise ValueError(
                    "The selected file contains no probe points."
                )

            self.autolevel_points = []

            for point in points:

                self.autolevel_points.append(
                    {
                        "x": float(point["x"]),
                        "y": float(point["y"]),
                        "z": float(point["z"])
                    }
                )

            if "x_min" in data:
                self.al_x_min.setValue(
                    float(data["x_min"])
                )

            if "x_max" in data:
                self.al_x_max.setValue(
                    float(data["x_max"])
                )

            if "y_min" in data:
                self.al_y_min.setValue(
                    float(data["y_min"])
                )

            if "y_max" in data:
                self.al_y_max.setValue(
                    float(data["y_max"])
                )

            if "z_min" in data:
                self.al_z_min.setValue(
                    float(data["z_min"])
                )

            if "z_max" in data:
                self.al_z_max.setValue(
                    float(data["z_max"])
                )

            if "resolution" in data:
                self.al_resolution.setValue(
                    float(data["resolution"])
                )

            if "probe_feed" in data:
                self.al_probe_feed.setValue(
                    float(data["probe_feed"])
                )

            if "z_retract" in data:
                self.al_z_retract.setValue(
                    float(data["z_retract"])
                )

            if "z_surface" in data:
                self.al_z_surface.setValue(
                    float(data["z_surface"])
                )

            if "probe_x_offset" in data:
                self.al_probe_x_offset.setValue(
                    float(data["probe_x_offset"])
                )

            if "probe_y_offset" in data:
                self.al_probe_y_offset.setValue(
                    float(data["probe_y_offset"])
                )

            if "probe_z_offset" in data:
                self.al_probe_z_offset.setValue(
                    float(data["probe_z_offset"])
                )

            self.populate_autolevel_table()

            self.update_autolevel_heatmap()

            self.al_progress.setValue(
                100
            )

            self.autolevel_status_label.setText(
                f"SURFACE MAP: "
                f"{len(self.autolevel_points)} POINTS"
            )

            self.log(
                f"AUTOLEVEL MAP LOADED: "
                f"{os.path.basename(path)}"
            )

            self.update_button_state()

        except Exception as e:

            QtWidgets.QMessageBox.critical(
                self,
                "Load AutoLevel",
                str(e)
            )

    # =========================================================
    # POPULATE AUTOLEVEL TABLE
    # =========================================================

    def populate_autolevel_table(self):

        self.al_table.setRowCount(
            0
        )

        for index, point in enumerate(
            self.autolevel_points,
            start=1
        ):

            row = self.al_table.rowCount()

            self.al_table.insertRow(
                row
            )

            values = [
                str(index),
                f"{point['x']:.4f}",
                f"{point['y']:.4f}",
                f"{point['z']:.4f}"
            ]

            for column, value in enumerate(
                values
            ):

                self.al_table.setItem(
                    row,
                    column,
                    QtWidgets.QTableWidgetItem(
                        value
                    )
                )

    # =========================================================
    # AUTOLEVEL 3D HEAT MAP
    # =========================================================

    def autolevel_heat_color(self, value, minimum, maximum):

        if (
            maximum
            -
            minimum
        ) <= 0.000000001:

            t = 0.5

        else:

            t = (
                value
                -
                minimum
            ) / (
                maximum
                -
                minimum
            )

        t = max(
            0.0,
            min(
                1.0,
                t
            )
        )

        # Five-point heat-map gradient:
        # blue -> cyan -> green -> yellow -> red

        stops = [
            (0.00, (0.05, 0.15, 1.00)),
            (0.25, (0.00, 0.85, 1.00)),
            (0.50, (0.10, 0.90, 0.20)),
            (0.75, (1.00, 0.85, 0.00)),
            (1.00, (1.00, 0.05, 0.05))
        ]

        for index in range(
            len(stops) - 1
        ):

            left_t, left_color = stops[index]
            right_t, right_color = stops[index + 1]

            if t <= right_t:

                span = (
                    right_t
                    -
                    left_t
                )

                if span <= 0:
                    local_t = 0.0
                else:
                    local_t = (
                        t
                        -
                        left_t
                    ) / span

                return (
                    left_color[0]
                    +
                    (
                        right_color[0]
                        -
                        left_color[0]
                    )
                    * local_t,

                    left_color[1]
                    +
                    (
                        right_color[1]
                        -
                        left_color[1]
                    )
                    * local_t,

                    left_color[2]
                    +
                    (
                        right_color[2]
                        -
                        left_color[2]
                    )
                    * local_t,

                    1.0
                )

        return (
            1.0,
            0.05,
            0.05,
            1.0
        )

    def update_autolevel_heatmap(self):

        if not hasattr(
            self,
            "al_heatmap_surface"
        ):

            return

        points = []

        for point in self.autolevel_points:

            try:

                x = float(
                    point["x"]
                )

                y = float(
                    point["y"]
                )

                z = float(
                    point["z"]
                )

                if all(
                    np.isfinite(
                        value
                    )
                    for value in [
                        x,
                        y,
                        z
                    ]
                ):

                    points.append(
                        (
                            x,
                            y,
                            z
                        )
                    )

            except (
                KeyError,
                TypeError,
                ValueError
            ):

                continue

        if not points:

            self.clear_autolevel_heatmap()

            return

        # -----------------------------------------------------
        # Sort the measured coordinates into a rectangular grid.
        # -----------------------------------------------------

        xs = sorted(
            set(
                round(
                    point[0],
                    9
                )
                for point in points
            )
        )

        ys = sorted(
            set(
                round(
                    point[1],
                    9
                )
                for point in points
            )
        )

        lookup = {
            (
                round(x, 9),
                round(y, 9)
            ): z

            for x, y, z in points
        }

        z_values = [
            point[2]
            for point in points
        ]

        z_min = min(
            z_values
        )

        z_max = max(
            z_values
        )

        # -----------------------------------------------------
        # Build vertices.
        #
        # The actual measured Z values are preserved, but the
        # vertical display is exaggerated so small bed errors
        # are easy to see.
        # -----------------------------------------------------

        z_range = max(
            z_max - z_min,
            0.001
        )

        xy_span = max(
            max(xs) - min(xs),
            max(ys) - min(ys),
            1.0
        )

        z_exaggeration = min(
            25.0,
            max(
                5.0,
                xy_span / (
                    z_range * 8.0
                )
            )
        )

        display_base = (
            z_min
        )

        vertices = []
        vertex_lookup = {}

        for y in ys:

            for x in xs:

                key = (
                    round(x, 9),
                    round(y, 9)
                )

                if key not in lookup:

                    continue

                z = lookup[key]

                display_z = (
                    z
                    -
                    display_base
                ) * z_exaggeration

                vertex_lookup[key] = len(
                    vertices
                )

                vertices.append(
                    [
                        x,
                        y,
                        display_z
                    ]
                )

        if not vertices:

            self.clear_autolevel_heatmap()

            return

        # -----------------------------------------------------
        # Build two triangles for every complete grid cell.
        # -----------------------------------------------------

        faces = []
        face_colors = []

        for y_index in range(
            len(ys) - 1
        ):

            for x_index in range(
                len(xs) - 1
            ):

                x1 = round(
                    xs[x_index],
                    9
                )

                x2 = round(
                    xs[x_index + 1],
                    9
                )

                y1 = round(
                    ys[y_index],
                    9
                )

                y2 = round(
                    ys[y_index + 1],
                    9
                )

                keys = [
                    (x1, y1),
                    (x2, y1),
                    (x2, y2),
                    (x1, y2)
                ]

                if not all(
                    key in vertex_lookup
                    for key in keys
                ):

                    continue

                a = vertex_lookup[
                    keys[0]
                ]

                b = vertex_lookup[
                    keys[1]
                ]

                c = vertex_lookup[
                    keys[2]
                ]

                d = vertex_lookup[
                    keys[3]
                ]

                faces.append(
                    [
                        a,
                        b,
                        c
                    ]
                )

                faces.append(
                    [
                        a,
                        c,
                        d
                    ]
                )

                z_average = (
                    lookup[keys[0]]
                    +
                    lookup[keys[1]]
                    +
                    lookup[keys[2]]
                    +
                    lookup[keys[3]]
                ) / 4.0

                color = self.autolevel_heat_color(
                    z_average,
                    z_min,
                    z_max
                )

                face_colors.append(
                    color
                )

                face_colors.append(
                    color
                )

        if faces:

            mesh = gl.MeshData(
                vertexes=np.asarray(
                    vertices,
                    dtype=float
                ),
                faces=np.asarray(
                    faces,
                    dtype=np.int32
                ),
                faceColors=np.asarray(
                    face_colors,
                    dtype=float
                )
            )

            self.al_heatmap_surface.setMeshData(
                meshdata=mesh
            )

        else:

            self.al_heatmap_surface.setMeshData(
                meshdata=gl.MeshData()
            )

        # -----------------------------------------------------
        # Show the actual probe locations as white points.
        # -----------------------------------------------------

        scatter = []

        for x, y, z in points:

            display_z = (
                z
                -
                display_base
            ) * z_exaggeration

            scatter.append(
                [
                    x,
                    y,
                    display_z
                ]
            )

        self.al_heatmap_points.setData(
            pos=np.asarray(
                scatter,
                dtype=float
            ),
            size=7,
            color=(1.0, 1.0, 1.0, 1.0),
            pxMode=True
        )

        # -----------------------------------------------------
        # Resize the grid around the scanned area.
        # -----------------------------------------------------

        x_span = max(
            max(xs) - min(xs),
            1.0
        )

        y_span = max(
            max(ys) - min(ys),
            1.0
        )

        self.al_heatmap_grid.setSize(
            x_span * 1.15,
            y_span * 1.15
        )

        spacing_x = max(
            1.0,
            x_span / 10.0
        )

        spacing_y = max(
            1.0,
            y_span / 10.0
        )

        self.al_heatmap_grid.setSpacing(
            spacing_x,
            spacing_y
        )

        self.al_heatmap_status.setText(
            f"{len(points)} POINTS  |  "
            f"Z {z_min:.4f} → {z_max:.4f} mm  |  "
            f"Δ {z_max - z_min:.4f} mm"
        )

        # Only auto-fit when the first points arrive.
        if len(points) <= 2:

            self.autolevel_heatmap_fit()

    def autolevel_heatmap_fit(self):

        if not self.autolevel_points:

            return

        points = []

        for point in self.autolevel_points:

            try:

                x = float(
                    point["x"]
                )

                y = float(
                    point["y"]
                )

                z = float(
                    point["z"]
                )

                if all(
                    np.isfinite(
                        value
                    )
                    for value in [
                        x,
                        y,
                        z
                    ]
                ):

                    points.append(
                        (
                            x,
                            y,
                            z
                        )
                    )

            except (
                KeyError,
                TypeError,
                ValueError
            ):

                pass

        if not points:

            return

        minimum = np.min(
            np.asarray(
                points,
                dtype=float
            ),
            axis=0
        )

        maximum = np.max(
            np.asarray(
                points,
                dtype=float
            ),
            axis=0
        )

        centre_x = (
            minimum[0]
            +
            maximum[0]
        ) / 2.0

        centre_y = (
            minimum[1]
            +
            maximum[1]
        ) / 2.0

        centre_z = 0.0

        xy_size = max(
            maximum[0] - minimum[0],
            maximum[1] - minimum[1],
            20.0
        )

        self.al_heatmap_view.opts[
            "center"
        ] = QtGui.QVector3D(
            float(centre_x),
            float(centre_y),
            float(centre_z)
        )

        self.al_heatmap_view.setCameraPosition(
            distance=float(
                xy_size * 1.55
            ),
            elevation=30,
            azimuth=-45
        )

    def autolevel_heatmap_top(self):

        if not self.autolevel_points:

            return

        self.autolevel_heatmap_fit()

        self.al_heatmap_view.setCameraPosition(
            elevation=90,
            azimuth=-90
        )

    def autolevel_heatmap_iso(self):

        if not self.autolevel_points:

            return

        self.autolevel_heatmap_fit()

        self.al_heatmap_view.setCameraPosition(
            elevation=30,
            azimuth=-45
        )

    def clear_autolevel_heatmap(self):

        if not hasattr(
            self,
            "al_heatmap_surface"
        ):

            return

        self.al_heatmap_surface.setMeshData(
            meshdata=gl.MeshData()
        )

        self.al_heatmap_points.setData(
            pos=np.empty(
                (0, 3),
                dtype=float
            )
        )

        self.al_heatmap_status.setText(
            "NO SURFACE DATA"
        )


    # =========================================================
    # SURFACE INTERPOLATION
    # =========================================================

    def surface_height(
        self,
        x,
        y
    ):

        if not self.autolevel_points:

            return None

        points = self.autolevel_points

        xs = sorted(
            set(
                round(
                    point["x"],
                    9
                )
                for point in points
            )
        )

        ys = sorted(
            set(
                round(
                    point["y"],
                    9
                )
                for point in points
            )
        )

        if not xs or not ys:

            return None

        # -----------------------------------------------------
        # Clamp to scanned area.
        # -----------------------------------------------------

        x = max(
            xs[0],
            min(
                xs[-1],
                float(x)
            )
        )

        y = max(
            ys[0],
            min(
                ys[-1],
                float(y)
            )
        )

        lookup = {}

        for point in points:

            lookup[
                (
                    round(
                        point["x"],
                        9
                    ),
                    round(
                        point["y"],
                        9
                    )
                )
            ] = float(
                point["z"]
            )

        # -----------------------------------------------------
        # Find surrounding X coordinates.
        # -----------------------------------------------------

        x1 = xs[0]
        x2 = xs[-1]

        for value in xs:

            if value <= x:
                x1 = value

            if value >= x:

                x2 = value

                break

        # -----------------------------------------------------
        # Find surrounding Y coordinates.
        # -----------------------------------------------------

        y1 = ys[0]
        y2 = ys[-1]

        for value in ys:

            if value <= y:
                y1 = value

            if value >= y:

                y2 = value

                break

        z11 = lookup.get(
            (
                round(x1, 9),
                round(y1, 9)
            )
        )

        z21 = lookup.get(
            (
                round(x2, 9),
                round(y1, 9)
            )
        )

        z12 = lookup.get(
            (
                round(x1, 9),
                round(y2, 9)
            )
        )

        z22 = lookup.get(
            (
                round(x2, 9),
                round(y2, 9)
            )
        )

        # -----------------------------------------------------
        # Handle incomplete maps safely.
        # -----------------------------------------------------

        available = [
            value
            for value in [
                z11,
                z21,
                z12,
                z22
            ]
            if value is not None
        ]

        if not available:

            return None

        if len(available) < 4:

            return float(
                np.mean(
                    available
                )
            )

        # -----------------------------------------------------
        # Bilinear interpolation.
        # -----------------------------------------------------

        if abs(
            x2 - x1
        ) < 0.000000001:

            tx = 0.0

        else:

            tx = (
                x - x1
            ) / (
                x2 - x1
            )

        if abs(
            y2 - y1
        ) < 0.000000001:

            ty = 0.0

        else:

            ty = (
                y - y1
            ) / (
                y2 - y1
            )

        z_bottom = (
            z11
            +
            (
                z21
                -
                z11
            )
            *
            tx
        )

        z_top = (
            z12
            +
            (
                z22
                -
                z12
            )
            *
            tx
        )

        return (
            z_bottom
            +
            (
                z_top
                -
                z_bottom
            )
            *
            ty
        )

    # =========================================================
    # APPLY AUTOLEVEL TO GCODE
    # =========================================================

    def apply_autolevel_to_gcode(self):

        if not self.gcode_lines:

            QtWidgets.QMessageBox.warning(
                self,
                "AutoLevel",
                "Load a G-code file first."
            )

            return

        if not self.autolevel_points:

            QtWidgets.QMessageBox.warning(
                self,
                "AutoLevel",
                "There is no surface map.\n\n"
                "Run an AutoLevel scan or load a saved map."
            )

            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):

            return

        answer = QtWidgets.QMessageBox.warning(
            self,
            "Apply AutoLevel",
            "Apply the measured surface map to the "
            "currently loaded G-code?\n\n"
            "The original G-code will be retained and "
            "can be restored.",
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No
        )

        if answer != QtWidgets.QMessageBox.Yes:

            return

        source = list(
            self.original_gcode_lines
            if self.original_gcode_lines
            else self.gcode_lines
        )

        levelled = self.compensate_gcode(
            source
        )

        if not levelled:

            QtWidgets.QMessageBox.warning(
                self,
                "AutoLevel",
                "No G-code could be generated."
            )

            return

        self.gcode_lines = levelled

        self.gcode_is_levelled = True

        self.gcode_editor.setPlainText(
            "".join(
                self.gcode_lines
            )
        )

        filename = os.path.basename(
            self.current_file
        )

        self.file_label.setText(
            f"{filename}\n"
            f"{len(self.gcode_lines):,} lines\n"
            f"AUTOLEVEL APPLIED"
        )

        self.gcode_editor.clear_highlight()

        self.gcode_line_label.setText(
            f"LINE 0 / "
            f"{len(self.gcode_lines):,}"
        )

        self.plot_gcode()

        self.log(
            "AUTOLEVEL SURFACE COMPENSATION APPLIED"
        )

        self.update_button_state()

    # =========================================================
    # COMPENSATE GCODE
    # =========================================================

    def compensate_gcode(
        self,
        source_lines
    ):

        result = []

        x = 0.0
        y = 0.0
        z = 0.0

        absolute = True
        motion = None

        previous_correction = 0.0

        z_surface = self.al_z_surface.value()

        def number(pattern, text):

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                try:

                    return float(
                        match.group(1)
                    )

                except Exception:

                    return None

            return None

        for original_line in source_lines:

            newline = (
                "\n"
                if original_line.endswith("\n")
                else ""
            )

            line_without_newline = (
                original_line.rstrip(
                    "\r\n"
                )
            )

            # -------------------------------------------------
            # Preserve blank lines.
            # -------------------------------------------------

            if not line_without_newline.strip():

                result.append(
                    original_line
                )

                continue

            # -------------------------------------------------
            # Separate semicolon comment.
            # -------------------------------------------------

            code_part = line_without_newline

            comment = ""

            if ";" in code_part:

                code_part, comment = (
                    code_part.split(
                        ";",
                        1
                    )
                )

                comment = ";" + comment

            # -------------------------------------------------
            # Remove parenthesis comments for parsing.
            # -------------------------------------------------

            parse_line = re.sub(
                r"\([^)]*\)",
                "",
                code_part
            )

            upper = parse_line.upper()

            # -------------------------------------------------
            # Distance mode.
            # -------------------------------------------------

            if re.search(
                r"(?<![A-Z0-9])G90(?![A-Z0-9])",
                upper
            ):

                absolute = True

            if re.search(
                r"(?<![A-Z0-9])G91(?![A-Z0-9])",
                upper
            ):

                absolute = False

            # -------------------------------------------------
            # Motion mode.
            # -------------------------------------------------

            motion_match = re.search(
                r"(?<![A-Z0-9])G0*([0-3])(?=$|\s|[XYZIJKF])",
                upper
            )

            if motion_match:

                motion = (
                    "G"
                    +
                    motion_match.group(1)
                )

            # -------------------------------------------------
            # Current position.
            # -------------------------------------------------

            start_x = x
            start_y = y
            start_z = z

            target_x = x
            target_y = y
            target_z = z

            x_value = number(
                r"X\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                upper
            )

            y_value = number(
                r"Y\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                upper
            )

            z_value = number(
                r"Z\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                upper
            )

            if x_value is not None:

                if absolute:

                    target_x = x_value

                else:

                    target_x += x_value

            if y_value is not None:

                if absolute:

                    target_y = y_value

                else:

                    target_y += y_value

            if z_value is not None:

                if absolute:

                    target_z = z_value

                else:

                    target_z += z_value

            # -------------------------------------------------
            # Only compensate cutting moves.
            # Rapid moves remain unchanged.
            # -------------------------------------------------

            cutting_move = (
                motion == "G1"
                or
                motion == "G2"
                or
                motion == "G3"
            )

            if cutting_move:

                correction = (
                    self.surface_height(
                        target_x,
                        target_y
                    )
                )

                if correction is not None:

                    correction = (
                        correction
                        -
                        z_surface
                    )

                    # -------------------------------------------------
                    # For absolute G-code:
                    #
                    # programmed Z + surface correction
                    # -------------------------------------------------

                    if absolute:

                        if (
                            z_value is not None
                            or
                            x_value is not None
                            or
                            y_value is not None
                        ):

                            compensated_z = (
                                target_z
                                +
                                correction
                            )

                            # -------------------------------------------------
                            # Replace existing Z word or append one.
                            # -------------------------------------------------

                            if re.search(
                                r"Z\s*[-+]?(?:\d+(?:\.\d*)?|\.\d+)",
                                code_part,
                                re.IGNORECASE
                            ):

                                code_part = re.sub(
                                    r"Z\s*[-+]?(?:\d+(?:\.\d*)?|\.\d+)",
                                    f"Z{compensated_z:.4f}",
                                    code_part,
                                    count=1,
                                    flags=re.IGNORECASE
                                )

                            else:

                                code_part = (
                                    code_part.rstrip()
                                    +
                                    f" Z{compensated_z:.4f}"
                                )

                    # -------------------------------------------------
                    # Incremental G-code:
                    #
                    # Apply the change in surface height from the
                    # previous point rather than adding the absolute
                    # correction repeatedly.
                    # -------------------------------------------------

                    else:

                        delta_correction = (
                            correction
                            -
                            previous_correction
                        )

                        if (
                            abs(
                                delta_correction
                            )
                            >
                            0.0000001
                            or
                            z_value is not None
                            or
                            x_value is not None
                            or
                            y_value is not None
                        ):

                            if z_value is not None:

                                compensated_delta = (
                                    z_value
                                    +
                                    delta_correction
                                )

                                code_part = re.sub(
                                    r"Z\s*[-+]?(?:\d+(?:\.\d*)?|\.\d+)",
                                    f"Z{compensated_delta:.4f}",
                                    code_part,
                                    count=1,
                                    flags=re.IGNORECASE
                                )

                            elif (
                                x_value is not None
                                or
                                y_value is not None
                            ):

                                code_part = (
                                    code_part.rstrip()
                                    +
                                    f" Z{delta_correction:.4f}"
                                )

                    previous_correction = correction

            elif motion == "G0":

                # -------------------------------------------------
                # Rapids do not get surface compensation.
                # -------------------------------------------------

                previous_correction = (
                    self.surface_height(
                        target_x,
                        target_y
                    )
                    or
                    previous_correction
                )

            # -------------------------------------------------
            # Update modal position.
            # -------------------------------------------------

            x = target_x
            y = target_y
            z = target_z

            # -------------------------------------------------
            # Rebuild line.
            # -------------------------------------------------

            output_line = (
                code_part
                +
                comment
                +
                newline
            )

            result.append(
                output_line
            )

        return result

    # =========================================================
    # RESTORE ORIGINAL GCODE
    # =========================================================

    def restore_original_gcode(self):

        if not self.original_gcode_lines:

            return

        if (
            self.sender
            and
            self.sender.isRunning()
        ):

            return

        answer = QtWidgets.QMessageBox.question(
            self,
            "Restore Original G-code",
            "Restore the original unlevelled G-code?",
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No
        )

        if answer != QtWidgets.QMessageBox.Yes:

            return

        self.gcode_lines = list(
            self.original_gcode_lines
        )

        self.gcode_is_levelled = False

        self.gcode_editor.setPlainText(
            "".join(
                self.gcode_lines
            )
        )

        filename = os.path.basename(
            self.current_file
        )

        self.file_label.setText(
            f"{filename}\n"
            f"{len(self.gcode_lines):,} lines"
        )

        self.gcode_editor.clear_highlight()

        self.gcode_line_label.setText(
            f"LINE 0 / "
            f"{len(self.gcode_lines):,}"
        )

        self.plot_gcode()

        self.log(
            "ORIGINAL G-CODE RESTORED"
        )

        self.update_button_state()

    # =========================================================
    # EXPORT LEVELLED GCODE
    # =========================================================

    def export_levelled_gcode(self):

        if not self.gcode_lines:

            QtWidgets.QMessageBox.warning(
                self,
                "Export",
                "No G-code is loaded."
            )

            return

        if not self.gcode_is_levelled:

            answer = QtWidgets.QMessageBox.question(
                self,
                "Export",
                "The currently loaded G-code has not been "
                "AutoLevel compensated.\n\n"
                "Export it anyway?",
                QtWidgets.QMessageBox.Yes |
                QtWidgets.QMessageBox.No
            )

            if answer != QtWidgets.QMessageBox.Yes:

                return

        base_name = "levelled"

        if self.current_file:

            base_name = (
                os.path.splitext(
                    os.path.basename(
                        self.current_file
                    )
                )[0]
                +
                "_levelled"
            )

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Levelled G-code",
            base_name + ".nc",
            "G-code (*.nc *.gcode *.tap *.ngc)"
        )

        if not path:

            return

        try:

            with open(
                path,
                "w",
                encoding="utf-8"
            ) as file:

                file.writelines(
                    self.gcode_lines
                )

            self.log(
                f"LEVELLED G-CODE EXPORTED: "
                f"{os.path.basename(path)}"
            )

            QtWidgets.QMessageBox.information(
                self,
                "Export Complete",
                "Levelled G-code exported successfully."
            )

        except Exception as e:

            QtWidgets.QMessageBox.critical(
                self,
                "Export Error",
                str(e)
            )

    # =========================================================
    # 3D GCODE VISUALISER
    # =========================================================

    def plot_gcode(self):

        self.cut_points_3d = []
        self.rapid_points_3d = []
        self.preview_z_offset = 0.0

        x = 0.0
        y = 0.0
        z = 0.0

        absolute = True

        motion = None

        spindle_on = False
        spindle_power = 0.0

        def number(pattern, text):

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                try:
                    return float(match.group(1))
                except Exception:
                    return None

            return None

        def has_code(code, text):

            return re.search(
                rf"(?<![A-Z0-9]){code}(?![A-Z0-9])",
                text,
                re.IGNORECASE
            ) is not None

        def add_segment(target, start, end):

            start = np.asarray(
                start,
                dtype=float
            )

            end = np.asarray(
                end,
                dtype=float
            )

            if np.allclose(
                start,
                end
            ):
                return

            target.append(start)
            target.append(end)

        def add_arc(
            target,
            start,
            end,
            clockwise,
            i_value,
            j_value
        ):

            if (
                i_value is None
                and
                j_value is None
            ):

                add_segment(
                    target,
                    start,
                    end
                )

                return

            i_value = (
                i_value
                if i_value is not None
                else 0.0
            )

            j_value = (
                j_value
                if j_value is not None
                else 0.0
            )

            cx = start[0] + i_value
            cy = start[1] + j_value

            radius = np.hypot(
                start[0] - cx,
                start[1] - cy
            )

            if radius <= 0.000001:

                add_segment(
                    target,
                    start,
                    end
                )

                return

            start_angle = np.arctan2(
                start[1] - cy,
                start[0] - cx
            )

            end_angle = np.arctan2(
                end[1] - cy,
                end[0] - cx
            )

            if clockwise:

                while end_angle >= start_angle:

                    end_angle -= 2.0 * np.pi

            else:

                while end_angle <= start_angle:

                    end_angle += 2.0 * np.pi

            sweep = (
                end_angle
                -
                start_angle
            )

            segments = max(
                12,
                int(
                    abs(sweep)
                    *
                    180.0
                    /
                    np.pi
                    /
                    4.0
                )
            )

            angles = np.linspace(
                start_angle,
                end_angle,
                segments + 1
            )

            points = []

            for angle in angles:

                px = (
                    cx
                    +
                    radius
                    *
                    np.cos(angle)
                )

                py = (
                    cy
                    +
                    radius
                    *
                    np.sin(angle)
                )

                if abs(
                    end[2] - start[2]
                ) > 0.000001:

                    fraction = (
                        angle
                        -
                        start_angle
                    ) / sweep

                    pz = (
                        start[2]
                        +
                        (
                            end[2]
                            -
                            start[2]
                        )
                        *
                        fraction
                    )

                else:

                    pz = start[2]

                points.append(
                    [
                        px,
                        py,
                        pz
                    ]
                )

            for i in range(
                len(points) - 1
            ):

                add_segment(
                    target,
                    points[i],
                    points[i + 1]
                )

        for raw_line in self.gcode_lines:

            line = re.sub(
                r"\([^)]*\)",
                "",
                raw_line
            )

            line = line.split(
                ";",
                1
            )[0].strip()

            if not line:
                continue

            line = re.sub(
                r"^\s*N[-+]?\d+\s*",
                "",
                line,
                flags=re.IGNORECASE
            )

            if not line:
                continue

            upper = line.upper()

            if re.search(
                r"(?<![A-Z0-9])G90(?![A-Z0-9])",
                upper
            ):

                absolute = True

            if re.search(
                r"(?<![A-Z0-9])G91(?![A-Z0-9])",
                upper
            ):

                absolute = False

            motion_match = re.search(
                r"(?<![A-Z0-9])G0*([0-3])(?=$|\s|[XYZIJKF])",
                upper
            )

            if motion_match:

                motion = "G" + motion_match.group(1)

            if re.search(
                r"(?<![A-Z0-9])M0*3(?![A-Z0-9])",
                upper
            ):

                spindle_on = True

            if re.search(
                r"(?<![A-Z0-9])M0*4(?![A-Z0-9])",
                upper
            ):

                spindle_on = True

            if re.search(
                r"(?<![A-Z0-9])M0*5(?![A-Z0-9])",
                upper
            ):

                spindle_on = False

            s_value = number(
                r"S\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                upper
            )

            if s_value is not None:

                spindle_power = s_value

                if s_value > 0:

                    spindle_on = True

            start = np.array(
                [
                    x,
                    y,
                    z
                ],
                dtype=float
            )

            tx = x
            ty = y
            tz = z

            x_value = number(
                r"X\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                upper
            )

            if x_value is not None:

                if absolute:

                    tx = x_value

                else:

                    tx += x_value

            y_value = number(
                r"Y\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                upper
            )

            if y_value is not None:

                if absolute:

                    ty = y_value

                else:

                    ty += y_value

            z_value = number(
                r"Z\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                upper
            )

            if z_value is not None:

                if absolute:

                    tz = z_value

                else:

                    tz += z_value

            end = np.array(
                [
                    tx,
                    ty,
                    tz
                ],
                dtype=float
            )

            moved = not np.allclose(
                start,
                end,
                atol=0.000001
            )

            if moved:

                if motion == "G0":

                    add_segment(
                        self.rapid_points_3d,
                        start,
                        end
                    )

                elif motion == "G1":

                    add_segment(
                        self.cut_points_3d,
                        start,
                        end
                    )

                elif motion == "G2":

                    i_value = number(
                        r"I\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                        upper
                    )

                    j_value = number(
                        r"J\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                        upper
                    )

                    add_arc(
                        self.cut_points_3d,
                        start,
                        end,
                        True,
                        i_value,
                        j_value
                    )

                elif motion == "G3":

                    i_value = number(
                        r"I\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                        upper
                    )

                    j_value = number(
                        r"J\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))",
                        upper
                    )

                    add_arc(
                        self.cut_points_3d,
                        start,
                        end,
                        False,
                        i_value,
                        j_value
                    )

                else:

                    add_segment(
                        self.rapid_points_3d,
                        start,
                        end
                    )

            x = tx
            y = ty
            z = tz

        if self.cut_points_3d:

            self.cut_points_3d = np.asarray(
                self.cut_points_3d,
                dtype=float
            )

        else:

            self.cut_points_3d = np.empty(
                (0, 3),
                dtype=float
            )

        if self.rapid_points_3d:

            self.rapid_points_3d = np.asarray(
                self.rapid_points_3d,
                dtype=float
            )

        else:

            self.rapid_points_3d = np.empty(
                (0, 3),
                dtype=float
            )

        # -----------------------------------------------------
        # VISUAL PREVIEW Z BASELINE
        # Keep negative-depth / multi-layer toolpaths above the
        # preview grid while preserving their relative Z heights.
        # This changes preview coordinates only, not the G-code
        # sent to the CNC controller.
        # -----------------------------------------------------

        z_arrays = []

        if len(self.cut_points_3d):
            z_arrays.append(self.cut_points_3d)

        if len(self.rapid_points_3d):
            z_arrays.append(self.rapid_points_3d)

        if z_arrays:
            all_preview_points = np.vstack(z_arrays)
            finite_z = all_preview_points[:, 2]
            finite_z = finite_z[np.isfinite(finite_z)]

            if len(finite_z):
                z_offset = float(np.min(finite_z))

                if z_offset < 0.0:
                    # Save the visual-only offset so the live red dot
                    # uses the exact same shifted Z coordinates.
                    self.preview_z_offset = -z_offset

                    if len(self.cut_points_3d):
                        self.cut_points_3d[:, 2] += self.preview_z_offset

                    if len(self.rapid_points_3d):
                        self.rapid_points_3d[:, 2] += self.preview_z_offset

        if len(
            self.cut_points_3d
        ) > 0:

            self.cut_3d.setData(
                pos=self.cut_points_3d,
                color=(0.0, 1.0, 1.0, 1.0),
                width=2,
                antialias=True,
                mode="lines"
            )

        else:

            self.cut_3d.setData(
                pos=np.empty(
                    (0, 3),
                    dtype=float
                ),
                color=(0.0, 1.0, 1.0, 1.0),
                width=2,
                antialias=True,
                mode="lines"
            )

        if len(
            self.rapid_points_3d
        ) > 0:

            self.rapid_3d.setData(
                pos=self.rapid_points_3d,
                color=(1.0, 0.0, 0.0, 1.0),
                width=1,
                antialias=True,
                mode="lines"
            )

        else:

            self.rapid_3d.setData(
                pos=np.empty(
                    (0, 3),
                    dtype=float
                ),
                color=(1.0, 0.0, 0.0, 1.0),
                width=1,
                antialias=True,
                mode="lines"
            )

        self.tool_3d.setData(
            pos=np.array(
                [[0.0, 0.0, 0.0]],
                dtype=float
            )
        )

        self.fit_visualiser()

    # =========================================================
    # FIT 3D VIEW
    # =========================================================

    def fit_visualiser(self):

        points = []

        if (
            isinstance(
                self.cut_points_3d,
                np.ndarray
            )
            and
            len(self.cut_points_3d)
        ):

            points.append(
                self.cut_points_3d
            )

        if (
            isinstance(
                self.rapid_points_3d,
                np.ndarray
            )
            and
            len(self.rapid_points_3d)
        ):

            points.append(
                self.rapid_points_3d
            )

        if not points:
            return

        all_points = np.vstack(
            points
        )

        all_points = all_points[
            np.all(
                np.isfinite(all_points),
                axis=1
            )
        ]

        if len(all_points) == 0:
            return

        minimum = np.min(
            all_points,
            axis=0
        )

        maximum = np.max(
            all_points,
            axis=0
        )

        centre = (
            minimum
            +
            maximum
        ) / 2.0

        size = np.max(
            maximum
            -
            minimum
        )

        if size <= 0:
            size = 100.0

        self.plot.opts["center"] = pg.Vector(
            float(centre[0]),
            float(centre[1]),
            float(centre[2])
        )

        self.plot.opts["distance"] = max(
            50.0,
            float(size * 1.6)
        )

        grid_size = max(
            200.0,
            float(size * 1.5)
        )

        grid_spacing = max(
            1.0,
            float(size / 20.0)
        )

        self.grid.setSize(
            grid_size,
            grid_size
        )

        self.grid.setSpacing(
            grid_spacing,
            grid_spacing
        )

        axis_length = max(
            100.0,
            float(size)
        )

        self.axis_x.setData(
            pos=np.array(
                [
                    [0, 0, 0],
                    [axis_length, 0, 0]
                ],
                dtype=float
            )
        )

        self.axis_y.setData(
            pos=np.array(
                [
                    [0, 0, 0],
                    [0, axis_length, 0]
                ],
                dtype=float
            )
        )

        self.axis_z.setData(
            pos=np.array(
                [
                    [0, 0, 0],
                    [0, 0, axis_length]
                ],
                dtype=float
            )
        )

        self.plot.update()

    # =========================================================
    # TOP VIEW
    # =========================================================

    def view_top(self):

        self.plot.setCameraPosition(
            elevation=90,
            azimuth=-90
        )

    # =========================================================
    # FRONT VIEW
    # =========================================================

    def view_front(self):

        self.plot.setCameraPosition(
            elevation=0,
            azimuth=-90
        )

    # =========================================================
    # RIGHT VIEW
    # =========================================================

    def view_right(self):

        self.plot.setCameraPosition(
            elevation=0,
            azimuth=0
        )

    # =========================================================
    # ISO VIEW
    # =========================================================

    def view_iso(self):

        self.plot.setCameraPosition(
            elevation=30,
            azimuth=-45
        )

    # =========================================================
    # CLEAR VISUALISER
    # =========================================================

    def clear_visualiser(self):

        self.cut_points_3d = np.empty(
            (0, 3),
            dtype=float
        )

        self.rapid_points_3d = np.empty(
            (0, 3),
            dtype=float
        )

        self.cut_3d.setData(
            pos=np.empty(
                (0, 3),
                dtype=float
            )
        )

        self.rapid_3d.setData(
            pos=np.empty(
                (0, 3),
                dtype=float
            )
        )

        self.tool_3d.setData(
            pos=np.array(
                [[0, 0, 0]],
                dtype=float
            )
        )

    # =========================================================
    # BUTTON STATE
    # =========================================================

    def update_button_state(self):

        connected = (
            self.ser is not None
            and
            self.ser.is_open
            if self.ser
            else False
        )

        running = (
            self.sender is not None
            and
            self.sender.isRunning()
        )

        autolevel_running = (
            self.autolevel_worker is not None
            and
            self.autolevel_worker.isRunning()
        )

        busy = (
            running
            or
            autolevel_running
        )

        for button in self.jog_buttons:

            button.setEnabled(
                connected
                and
                not busy
            )

        for button in self.zero_buttons:

            button.setEnabled(
                connected
                and
                not busy
            )

        self.spindle_cw_btn.setEnabled(
            connected
            and
            not busy
        )

        self.spindle_ccw_btn.setEnabled(
            connected
            and
            not busy
        )

        self.spindle_off_btn.setEnabled(
            connected
        )

        self.cmd_send_btn.setEnabled(
            connected
            and
            not busy
        )

        self.play_btn.setEnabled(
            connected
            and
            bool(self.gcode_lines)
            and
            not busy
        )

        self.pause_btn.setEnabled(
            running
            and
            not self.is_paused
        )

        self.resume_btn.setEnabled(
            running
            and
            self.is_paused
        )

        self.stop_btn.setEnabled(
            running
        )

        self.load_btn.setEnabled(
            not busy
        )

        self.clear_btn.setEnabled(
            not busy
        )

        self.home_btn.setEnabled(
            connected
            and
            not busy
        )

        self.unlock_btn.setEnabled(
            connected
            and
            not busy
        )

        self.reset_btn.setEnabled(
            connected
        )

        self.check_btn.setEnabled(
            bool(self.gcode_lines)
            and
            not busy
        )

        # -----------------------------------------------------
        # AUTOLEVEL BUTTONS
        # -----------------------------------------------------

        self.al_scan_btn.setEnabled(
            connected
            and
            not busy
        )

        self.al_stop_btn.setEnabled(
            autolevel_running
        )

        self.al_clear_btn.setEnabled(
            not busy
        )

        self.al_save_btn.setEnabled(
            bool(
                self.autolevel_points
            )
            and
            not busy
        )

        self.al_load_btn.setEnabled(
            not busy
        )

        self.al_apply_btn.setEnabled(
            bool(
                self.autolevel_points
            )
            and
            bool(
                self.gcode_lines
            )
            and
            not busy
        )

        self.al_restore_btn.setEnabled(
            bool(
                self.original_gcode_lines
            )
            and
            not busy
        )

        self.al_export_btn.setEnabled(
            bool(
                self.gcode_lines
            )
            and
            not busy
        )

    # =========================================================
    # LOG
    # =========================================================

    def log(self, message):

        timestamp = time.strftime(
            "%H:%M:%S"
        )

        self.log_box.append(
            f"[{timestamp}] {message}"
        )

        self.log_box.ensureCursorVisible()

    # =========================================================
    # CLOSE
    # =========================================================

    def closeEvent(self, event):

        if (
            self.autolevel_worker
            and
            self.autolevel_worker.isRunning()
        ):

            answer = QtWidgets.QMessageBox.warning(
                self,
                "AutoLevel Running",
                "An AutoLevel scan is currently running.\n\n"
                "Stop the scan and close?",
                QtWidgets.QMessageBox.Yes |
                QtWidgets.QMessageBox.No
            )

            if answer != QtWidgets.QMessageBox.Yes:

                event.ignore()

                return

            try:

                self.autolevel_worker.stop()

                self.ser.write(
                    b"\x18"
                )

                self.ser.flush()

            except Exception:
                pass

            self.autolevel_worker.wait(
                2000
            )

        if (
            self.sender
            and
            self.sender.isRunning()
        ):

            answer = QtWidgets.QMessageBox.warning(
                self,
                "Job Running",
                "A CNC job is currently running.\n\n"
                "Stop the machine and close?",
                QtWidgets.QMessageBox.Yes |
                QtWidgets.QMessageBox.No
            )

            if answer != QtWidgets.QMessageBox.Yes:

                event.ignore()

                return

            try:

                self.sender.stop()

                self.ser.write(
                    b"\x18"
                )

                self.ser.flush()

            except Exception:
                pass

            self.sender.wait(
                2000
            )

        if self.ser:

            try:

                self.ser.write(
                    b"M5\n"
                )

            except Exception:
                pass

            try:

                self.ser.close()

            except Exception:
                pass

        event.accept()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app = QtWidgets.QApplication(
        sys.argv
    )

    app.setApplicationName(
        APP_NAME
    )

    app.setApplicationVersion(
        APP_VERSION
    )

    app.setStyle(
        "Fusion"
    )

    window = CNCSender()

    window.show()

    sys.exit(
        app.exec_()
    )